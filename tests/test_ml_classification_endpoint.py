from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
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
        "login": "ana.operadora",
        "email": "ana.operadora@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa ML LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-ml",
        "cod_dominio": 7101,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(**overrides) -> ContaContabil:
    data = {
        "codigo": 50057,
        "classificacao": "3.1.01.01.50057",
        "nome": "FORNECEDORES",
        "tipo": "A",
        "grau": 5,
        "is_active": True,
        "is_financial_origin": False,
    }
    data.update(overrides)
    return ContaContabil(**data)


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


def _seed_user_company_and_account(permissao: str = "operacao"):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    conta = _conta()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, conta])
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


def _seed_inactive_user_company_and_account():
    from tests.conftest import TestingSessionLocal

    usuario = _usuario(is_active=False)
    empresa = _empresa()
    conta = _conta()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, conta])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario.id,
                empresa_id=empresa.id,
                permissao="operacao",
            )
        )
        session.commit()
        return _auth_headers(usuario), empresa.id, usuario.id


def _seed_user_without_company_link_and_account():
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    conta = _conta()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, conta])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        return _auth_headers(usuario), empresa.id, usuario.id


class ModeloMockado:
    classes_ = [50057, 70001]

    def __init__(self):
        self.features_seen = None

    def predict_proba(self, features):
        self.features_seen = features
        return [[0.91, 0.09] for _ in features]


class ModeloBaixaConfianca:
    classes_ = [50057, 70001]

    def predict_proba(self, features):
        return [[0.60, 0.40] for _ in features]


def _audit_events():
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        return session.query(AuditEvent).order_by(AuditEvent.id).all()


def test_classification_endpoint_returns_counterpart_prediction_with_probability(
    client, monkeypatch, tmp_path
):
    headers, empresa_id = _seed_user_company_and_account()
    model_path = tmp_path / f"empresa_{empresa_id}" / "model_.joblib"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"modelo mockado")
    model = ModeloMockado()
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr("core.ml_engine.joblib.load", lambda path: model)

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert model.features_seen == [
        "pagamento fornecedor origem_10046 direcao_credito"
    ]
    data = response.json()
    assert data == {
        "empresa_id": empresa_id,
        "quantidade_processada": 1,
        "results": [
            {
                "conta_contrapartida": 50057,
                "confianca": 0.91,
                "needs_review": False,
            }
        ],
    }


def test_classification_endpoint_creates_started_and_completed_audit_events(
    client, monkeypatch, tmp_path
):
    headers, empresa_id = _seed_user_company_and_account()
    model_path = tmp_path / f"empresa_{empresa_id}" / "model_.joblib"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"modelo mockado")
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(
        "core.ml_engine.joblib.load",
        lambda path: ModeloBaixaConfianca(),
    )

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 200
    events = _audit_events()
    assert [event.event_type for event in events] == [
        "classification.started",
        "classification.completed",
    ]
    started, completed = events
    assert started.empresa_id == empresa_id
    assert started.user_id is not None
    assert started.resource_id == "ml_classification"
    assert started.metadata_json == {"total_solicitado": 1}
    assert completed.empresa_id == empresa_id
    assert completed.user_id == started.user_id
    assert completed.resource_id == "ml_classification"
    assert completed.metadata_json == {
        "total_processado": 1,
        "total_revisao": 1,
    }
    assert "historico" not in completed.metadata_json


def test_classification_endpoint_returns_404_when_company_has_no_model(client):
    headers, empresa_id = _seed_user_company_and_account()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Modelo treinado não encontrado para a empresa"


def test_classification_endpoint_creates_failed_audit_event_when_model_is_missing(
    client,
):
    headers, empresa_id = _seed_user_company_and_account()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 404
    events = _audit_events()
    assert [event.event_type for event in events] == [
        "classification.started",
        "classification.failed",
    ]
    failed = events[1]
    assert failed.empresa_id == empresa_id
    assert failed.user_id is not None
    assert failed.resource_id == "ml_classification"
    assert failed.metadata_json == {
        "total_solicitado": 1,
        "error_type": "ModelNotFound",
        "reason": "model_not_found",
    }
    assert "historico" not in failed.metadata_json


def test_classification_endpoint_rejects_batches_over_100_items(
    client, monkeypatch, tmp_path
):
    headers, empresa_id = _seed_user_company_and_account()
    model_path = tmp_path / f"empresa_{empresa_id}" / "model_.joblib"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"modelo mockado")
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json=[
            {
                "historico": f"Pagamento Fornecedor {index}",
                "conta_origem": 10046,
                "direcao": "credito",
            }
            for index in range(101)
        ],
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Limite de 100 lançamentos por requisição"


def test_classification_endpoint_requires_jwt(client):
    _headers, empresa_id = _seed_user_company_and_account()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
    )

    assert response.status_code in (401, 403)


def test_classification_endpoint_requires_company_operation_permission(client):
    headers, empresa_id = _seed_user_company_and_account(permissao="leitura")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Permissão insuficiente"
    events = _audit_events()
    assert [event.event_type for event in events] == ["auth.access.denied"]
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json == {"reason": "insufficient_permission"}


def test_classification_endpoint_rejects_user_without_company_link_and_audits(
    client,
):
    headers, empresa_id, usuario_id = _seed_user_without_company_link_and_account()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso negado"
    events = _audit_events()
    assert [event.event_type for event in events] == ["auth.access.denied"]
    assert events[0].user_id == usuario_id
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json == {"reason": "access_denied"}


def test_classification_endpoint_rejects_inactive_user_and_audits(client):
    headers, empresa_id, usuario_id = _seed_inactive_user_company_and_account()

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json={
            "historico": "Pagamento Fornecedor",
            "conta_origem": 10046,
            "direcao": "credito",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Usuário inativo"
    events = _audit_events()
    assert [event.event_type for event in events] == ["auth.user.inactive_blocked"]
    assert events[0].user_id == usuario_id
    assert events[0].metadata_json == {"reason": "inactive_user"}



def test_classification_endpoint_loads_model_once_for_small_batch(
    client, monkeypatch, tmp_path
):
    headers, empresa_id = _seed_user_company_and_account()
    model_path = tmp_path / f"empresa_{empresa_id}" / "model_.joblib"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"modelo mockado")
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    load_calls = []

    def load_model(path):
        load_calls.append(path)
        return ModeloMockado()

    monkeypatch.setattr("core.ml_engine.joblib.load", load_model)

    response = client.post(
        f"/api/v1/companies/{empresa_id}/ml/classification",
        json=[
            {
                "historico": "Pagamento Fornecedor",
                "conta_origem": 10046,
                "direcao": "credito",
            },
            {
                "historico": "Pagamento Fornecedor 2",
                "conta_origem": 10046,
                "direcao": "credito",
            },
        ],
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["quantidade_processada"] == 2
    assert len(load_calls) == 1
