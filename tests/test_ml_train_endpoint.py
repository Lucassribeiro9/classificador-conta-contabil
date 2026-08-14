from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
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
        "nome": "Ana Treinamento",
        "login": "ana.treinamento",
        "email": "ana.treinamento@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Treino LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-treino",
        "cod_dominio": 8101,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(codigo: int, *, is_financial_origin: bool = False) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.1.{codigo}",
        nome=f"Conta {codigo}",
        tipo="A",
        grau=4,
        is_active=True,
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


def _lancamento(
    lote: LoteImportacaoRazao,
    empresa: Empresa,
    *,
    index: int,
    target: int,
) -> LancamentoRazaoNormalizado:
    return LancamentoRazaoNormalizado(
        lote=lote,
        empresa=empresa,
        numero_lancamento=str(index),
        data=date(2026, 1, 15),
        conta_origem=10046,
        conta_contrapartida=target,
        conta_debito=target,
        conta_credito=10046,
        direcao="credito",
        historico=f"Pagamento fornecedor {index}",
        historico_normalizado=f"pagamento fornecedor {index}",
        valor=Decimal("100.00"),
    )


def _seed_company_with_razao(*, permissao: str, targets: list[int]):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=usuario,
        original_filename="razao-treino.xlsx",
        file_hash=f"sha256:treino-{permissao}-{len(targets)}",
        status="completed",
    )
    contas = [
        _conta(10046, is_financial_origin=True),
        *[_conta(target) for target in sorted(set(targets))],
    ]
    lancamentos = [
        _lancamento(lote, empresa, index=index + 1, target=target)
        for index, target in enumerate(targets)
    ]

    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, lote, *contas, *lancamentos])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario.id,
                empresa_id=empresa.id,
                permissao=permissao,
            )
        )
        session.commit()
        return _auth_headers(usuario), empresa.id


def _audit_events():
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        return session.query(AuditEvent).order_by(AuditEvent.id).all()


def test_train_endpoint_trains_model_from_canonical_company_razao(
    client,
    monkeypatch,
    tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="operacao",
        targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/train",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "empresa_id": empresa_id,
        "total_linhas": 10,
        "total_descartes": 0,
        "contagem_por_target": {"50057": 5, "70001": 5},
        "treinavel": True,
        "status": "trained",
    }
    assert (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["model.trained"]
    assert events[0].empresa_id == empresa_id
    assert events[0].resource_id == f"empresa_{empresa_id}/model_.joblib"
    assert events[0].metadata_json["dataset_examples"] == 10
    assert "historico" not in events[0].metadata_json


def test_train_endpoint_returns_422_when_dataset_is_insufficient(
    client,
    monkeypatch,
    tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="operacao",
        targets=[50057],
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/train",
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Dataset insuficiente para treino do modelo"
    assert not (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["model.train_failed"]
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json["reason"] == "insufficient_dataset"
    assert events[0].metadata_json["dataset_examples"] == 1
    assert "historico" not in events[0].metadata_json


def test_train_endpoint_requires_company_operation_permission(
    client,
    monkeypatch,
    tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="leitura",
        targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/train",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Permissão insuficiente"
    assert not (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["auth.access.denied"]
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json == {"reason": "insufficient_permission"}
