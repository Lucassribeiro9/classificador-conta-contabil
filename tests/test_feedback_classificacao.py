from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.dataset_builder import build_dataset_treino_contrapartida
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    FeedbackClassificacao,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
    UsuarioEmpresaPermissao,
)


password_hash = PasswordHash.recommended()


@pytest.fixture(autouse=True)
def jwt_settings():
    previous_secret = settings.JWT_SECRET_KEY
    previous_algorithm = settings.JWT_ALGORITHM
    settings.JWT_SECRET_KEY = "test-secret"
    settings.JWT_ALGORITHM = "HS256"
    try:
        yield
    finally:
        settings.JWT_SECRET_KEY = previous_secret
        settings.JWT_ALGORITHM = previous_algorithm


def _usuario(**overrides) -> Usuario:
    data = {
        "nome": "Ana Operadora",
        "login": "ana.feedback",
        "email": "ana.feedback@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Feedback LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-feedback",
        "cod_dominio": 7201,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(
    codigo: int,
    *,
    tipo: str = "A",
    is_active: bool = True,
    is_financial_origin: bool = False,
) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.1.{codigo}",
        nome=f"Conta {codigo}",
        tipo=tipo,
        grau=4,
        is_active=is_active,
        is_financial_origin=is_financial_origin,
    )


def _access_token(usuario: Usuario) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(usuario.id),
            "role": usuario.papel,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=12),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _auth_headers(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token(usuario)}"}


def _seed_context():
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=usuario,
        original_filename="razao-feedback.xlsx",
        file_hash="sha256:feedback",
        status="completed",
    )
    lancamento = LancamentoRazaoNormalizado(
        lote=lote,
        empresa=empresa,
        numero_lancamento="42",
        data=date(2026, 1, 15),
        conta_origem=10046,
        conta_contrapartida=50057,
        conta_debito=50057,
        conta_credito=10046,
        direcao="credito",
        historico="Pagamento fornecedor",
        historico_normalizado="pagamento fornecedor",
        valor=Decimal("2500.00"),
    )
    with TestingSessionLocal() as session:
        session.add_all(
            [
                usuario,
                empresa,
                _conta(10046, is_financial_origin=True),
                _conta(50057),
                _conta(70001),
                lote,
                lancamento,
            ]
        )
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.refresh(lancamento)
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario.id,
                empresa_id=empresa.id,
                permissao="operacao",
            )
        )
        session.commit()
        return _auth_headers(usuario), empresa.id, usuario.id, lancamento.id


def test_feedback_classificacao_endpoint_persists_user_and_final_account(client):
    headers, empresa_id, usuario_id, lancamento_id = _seed_context()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 70001,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["empresa_id"] == empresa_id
    assert data["lancamento_id"] == lancamento_id
    assert data["conta_sugerida"] == 50057
    assert data["conta_final"] == 70001
    assert data["usuario_id"] == usuario_id

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        feedback = session.query(FeedbackClassificacao).one()
        assert feedback.empresa_id == empresa_id
        assert feedback.lancamento_id == lancamento_id
        assert feedback.conta_sugerida == 50057
        assert feedback.conta_final == 70001
        assert feedback.usuario_id == usuario_id


def test_feedback_classificacao_created_audit_event_has_safe_metadata(client):
    headers, empresa_id, usuario_id, lancamento_id = _seed_context()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 70001,
        },
        headers=headers,
    )

    assert response.status_code == 200

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        feedback = session.query(FeedbackClassificacao).one()
        assert event.event_type == "feedback.created"
        assert event.user_id == usuario_id
        assert event.empresa_id == empresa_id
        assert event.resource_id == str(feedback.id)
        assert event.metadata_json == {
            "lancamento_id": lancamento_id,
            "conta_anterior": 50057,
            "conta_corrigida": 70001,
        }
        assert "historico" not in event.metadata_json
        assert "token" not in event.metadata_json


def test_feedback_classificacao_updated_audit_event_uses_previous_final_account(
    client,
):
    headers, empresa_id, usuario_id, lancamento_id = _seed_context()

    first_response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 70001,
        },
        headers=headers,
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 70001,
            "conta_final": 50057,
        },
        headers=headers,
    )

    assert second_response.status_code == 200

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        events = session.query(AuditEvent).order_by(AuditEvent.id).all()
        assert [event.event_type for event in events] == [
            "feedback.created",
            "feedback.updated",
        ]
        updated = events[1]
        latest_feedback = (
            session.query(FeedbackClassificacao)
            .order_by(FeedbackClassificacao.id.desc())
            .first()
        )
        assert updated.user_id == usuario_id
        assert updated.empresa_id == empresa_id
        assert updated.resource_id == str(latest_feedback.id)
        assert updated.metadata_json == {
            "lancamento_id": lancamento_id,
            "conta_anterior": 70001,
            "conta_corrigida": 50057,
        }


def test_feedback_classificacao_invalid_final_account_does_not_audit(client):
    headers, empresa_id, _usuario_id, lancamento_id = _seed_context()

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(_conta(90001, tipo="S"))
        session.commit()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 90001,
        },
        headers=headers,
    )

    assert response.status_code == 422
    with TestingSessionLocal() as session:
        assert session.query(AuditEvent).all() == []


def test_dataset_builder_uses_feedback_final_account_as_target(client):
    headers, empresa_id, _usuario_id, lancamento_id = _seed_context()
    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 70001,
        },
        headers=headers,
    )
    assert response.status_code == 200

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa_id)

    assert dataset.linhas == [
        {
            "features": "pagamento fornecedor origem_10046 direcao_credito",
            "target_conta_contrapartida": 70001,
        }
    ]
    assert dataset.metadata["contagem_por_target"] == {70001: 1}


def test_feedback_classificacao_rejects_synthetic_final_account(client):
    headers, empresa_id, _usuario_id, lancamento_id = _seed_context()

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(_conta(90001, tipo="S"))
        session.commit()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/feedback",
        json={
            "lancamento_id": lancamento_id,
            "conta_sugerida": 50057,
            "conta_final": 90001,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Conta final deve ser analítica e ativa"
