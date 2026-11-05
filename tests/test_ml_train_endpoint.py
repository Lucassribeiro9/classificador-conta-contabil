from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.ml_worker import MLWorker
from core.plano_contas_snapshots import importar_snapshot
from core.models import (
    AuditEvent,
    ContaContabil,
    ContaContabilEmpresa,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
    UsuarioEmpresaPermissao,
)


password_hash = PasswordHash.recommended()


def _train_and_wait(client, url: str, *, headers: dict):
    """Exercise the async API and worker for model lifecycle assertions."""
    from tests.conftest import TestingSessionLocal

    accepted = client.post(url, headers={**headers, "Idempotency-Key": uuid4().hex})
    if accepted.status_code != 202:
        return accepted
    worker = MLWorker(TestingSessionLocal, worker_id="test-train", model_dir=settings.MODEL_DIR)
    assert worker.run_once()
    status = client.get(accepted.json()["status_url"], headers=headers).json()
    if status["status"] == "failed":
        return httpx.Response(422, json={"message": "Dataset insuficiente para treino do modelo"})
    assert status["status"] == "completed", status
    return httpx.Response(200, json=status["result"])


def _classify_and_wait(client, url: str, *, headers: dict, payload: dict):
    from tests.conftest import TestingSessionLocal

    accepted = client.post(
        url, headers={**headers, "Idempotency-Key": uuid4().hex}, json=payload,
    )
    assert accepted.status_code == 202
    worker = MLWorker(TestingSessionLocal, worker_id="test-classify", model_dir=settings.MODEL_DIR)
    assert worker.run_once()
    status = client.get(accepted.json()["status_url"], headers=headers).json()
    if status["status"] == "failed" and status["error_code"] == "model_not_found":
        return httpx.Response(404, json={"message": "Modelo treinado não encontrado para a empresa"})
    assert status["status"] == "completed", status
    return httpx.Response(200, json=status["result"])


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
        importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=[{
                "codigo": account.codigo,
                "classificacao": account.classificacao,
                "nome": account.nome,
                "tipo": account.tipo,
                "grau": account.grau,
            } for account in contas],
            vigencia=date(2026, 1, 1),
            origem="teste-treino-dataset",
        )
        session.query(ContaContabilEmpresa).filter_by(
            empresa_id=empresa.id, codigo=10046
        ).one().is_financial_origin = True
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
        return (
            session.query(AuditEvent)
            .filter(AuditEvent.event_type != "plan.snapshot_imported")
            .order_by(AuditEvent.id)
            .all()
        )


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

    response = _train_and_wait(client, f"/api/v1/companies/{empresa_id}/ml/train", headers=headers)

    assert response.status_code == 200
    assert response.json() == {
        "empresa_id": empresa_id,
        "version_id": 1,
        "total_linhas": 10,
        "total_descartes": 0,
        "contagem_por_target": {"50057": 5, "70001": 5},
        "treinavel": True,
        "status": "candidate",
    }
    assert (tmp_path / f"empresa_{empresa_id}" / "model_1.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["model.candidate_created", "ml.job.completed"]
    assert events[0].empresa_id == empresa_id
    assert events[0].resource_id == "1"
    assert events[0].metadata_json["evaluation_method"] == "holdout"
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

    response = _train_and_wait(client, f"/api/v1/companies/{empresa_id}/ml/train", headers=headers)

    assert response.status_code == 422
    assert response.json()["message"] == "Dataset insuficiente para treino do modelo"
    assert not (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["ml.job.failed"]
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json["error_code"] == "insufficient_dataset"
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

    response = _train_and_wait(client, f"/api/v1/companies/{empresa_id}/ml/train", headers=headers)

    assert response.status_code == 403
    assert response.json()["message"] == "Permissão insuficiente"
    assert not (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()
    events = _audit_events()
    assert [event.event_type for event in events] == ["auth.access.denied"]
    assert events[0].empresa_id == empresa_id
    assert events[0].metadata_json == {"reason": "insufficient_permission"}


def test_training_creates_immutable_candidate_without_activating_it(
    client,
    monkeypatch,
    tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="operacao",
        targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = _train_and_wait(client, f"/api/v1/companies/{empresa_id}/ml/train", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "candidate"
    version_id = response.json()["version_id"]
    with TestingSessionLocal() as session:
        version = session.get(ModelVersion, version_id)
        assert version.empresa_id == empresa_id
        assert version.status == "candidate"
        assert version.manifest_id is not None
        assert version.evaluation["method"] in {"holdout", "stratified_kfold"}
        assert version.artifact_sha256
        assert session.query(ModelVersion).filter_by(
            empresa_id=empresa_id, status="active"
        ).count() == 0
    assert (tmp_path / f"empresa_{empresa_id}" / f"model_{version_id}.joblib").exists()
    assert not (tmp_path / f"empresa_{empresa_id}" / "model_.joblib").exists()


def test_admin_promotes_candidate_and_rolls_back_without_retraining(
    client,
    monkeypatch,
    tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"

    first = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    promoted = client.post(f"{base}/models/{first}/promote", headers=headers)
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "active"
    second = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    promoted_second = client.post(f"{base}/models/{second}/promote", headers=headers)
    assert promoted_second.status_code == 200
    assert promoted_second.json()["status"] == "active"

    rollback = client.post(f"{base}/models/{first}/rollback", headers=headers)
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "active"
    with TestingSessionLocal() as session:
        assert session.get(ModelVersion, first).status == "active"
        assert session.get(ModelVersion, second).status == "retired"
        assert session.get(ModelVersion, second).evaluation["comparison_version_id"] == first
        assert session.get(ModelVersion, second).evaluation["baseline_metrics"] is not None
        assert session.query(ModelVersion).filter_by(
            empresa_id=empresa_id, status="active"
        ).count() == 1
    assert (tmp_path / f"empresa_{empresa_id}" / f"model_{first}.joblib").exists()
    assert (tmp_path / f"empresa_{empresa_id}" / f"model_{second}.joblib").exists()


def test_admin_sets_critical_classes_before_evaluation_and_candidate_freezes_them(
    client, monkeypatch, tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    configured = client.request(
        "PUT", f"{base}/critical-classes", headers=headers, json={"classes": [50057]}
    )
    assert configured.status_code == 200
    first = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    cleared = client.request(
        "PUT", f"{base}/critical-classes", headers=headers, json={"classes": []}
    )
    assert cleared.status_code == 200
    second = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    with TestingSessionLocal() as session:
        assert session.get(ModelVersion, first).critical_classes == [50057]
        assert session.get(ModelVersion, second).critical_classes == []


def test_only_promoted_version_serves_company_classification(
    client, monkeypatch, tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    version_id = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    payload = {
        "historico": "Pagamento fornecedor 1",
        "conta_origem": 10046,
        "direcao": "credito",
    }
    before = _classify_and_wait(client, f"{base}/classification", headers=headers, payload=payload)
    assert before.status_code == 404

    assert client.post(f"{base}/models/{version_id}/promote", headers=headers).status_code == 200
    status = client.get(f"{base}/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["modelo_path"] == f"empresa_{empresa_id}/model_{version_id}.joblib"
    response = _classify_and_wait(client, f"{base}/classification", headers=headers, payload=payload)
    assert response.status_code == 200
    assert response.json()["model_version_id"] == version_id
    assert response.json()["results"][0]["conta_contrapartida"] in {50057, 70001}
    completed = [event for event in _audit_events() if event.event_type == "classification.completed"]
    assert completed[-1].metadata_json["model_version_id"] == version_id


def test_admin_can_inspect_candidate_evaluation_before_promotion(
    client, monkeypatch, tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    version_id = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]

    response = client.get(f"{base}/models", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["models"]) == 1
    model = response.json()["models"][0]
    assert model["id"] == version_id
    assert model["status"] == "candidate"
    assert model["manifest_id"] > 0
    assert model["evaluation"]["valid"] is True
    assert "macro_f1" in model["metrics"]
    assert model["threshold"] == 0.70


def test_promotion_rejects_candidate_below_active_guardrails(
    client, monkeypatch, tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    first = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    assert client.post(f"{base}/models/{first}/promote", headers=headers).status_code == 200
    second = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    with TestingSessionLocal() as session:
        candidate = session.get(ModelVersion, second)
        candidate.metrics = {
            "macro_f1": -1.0,
            "per_class_f1": {"50057": 0.0, "70001": 0.0},
        }
        session.commit()

    rejected = client.post(f"{base}/models/{second}/promote", headers=headers)

    assert rejected.status_code == 422
    assert "macro F1" in rejected.json()["message"]
    assert "model.promotion_denied" in [event.event_type for event in _audit_events()]
    with TestingSessionLocal() as session:
        assert session.get(ModelVersion, first).status == "active"
        assert session.get(ModelVersion, second).status == "candidate"


def test_small_dataset_uses_reproducible_cross_validation(
    client, monkeypatch, tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057] * 8 + [70001] * 2,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    response = _train_and_wait(client, f"/api/v1/companies/{empresa_id}/ml/train", headers=headers)
    assert response.status_code == 200
    version_id = response.json()["version_id"]
    models = client.get(f"/api/v1/companies/{empresa_id}/ml/models", headers=headers)
    evaluation = models.json()["models"][0]["evaluation"]
    assert models.json()["models"][0]["id"] == version_id
    assert evaluation["method"] == "stratified_kfold"
    assert evaluation["folds"] == 2


def test_operator_cannot_promote_model_candidate(client, monkeypatch, tmp_path):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    version_id = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]

    response = client.post(f"{base}/models/{version_id}/promote", headers=headers)

    assert response.status_code == 403
    with TestingSessionLocal() as session:
        assert session.get(ModelVersion, version_id).status == "candidate"


def test_critical_class_regression_blocks_promotion_even_with_higher_macro_f1(
    client, monkeypatch, tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    first = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    assert client.post(f"{base}/models/{first}/promote", headers=headers).status_code == 200
    configured = client.request(
        "PUT", f"{base}/critical-classes", headers=headers, json={"classes": [50057]}
    )
    assert configured.status_code == 200
    second = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    with TestingSessionLocal() as session:
        candidate = session.get(ModelVersion, second)
        baseline = session.get(ModelVersion, first)
        baseline_f1 = baseline.metrics["per_class_f1"]["50057"]
        candidate.metrics = {
            "macro_f1": baseline.metrics["macro_f1"] + 1.0,
            "per_class_f1": {"50057": baseline_f1 - 1.0, "70001": 1.0},
        }
        session.commit()

    response = client.post(f"{base}/models/{second}/promote", headers=headers)

    assert response.status_code == 422
    assert "classe critica" in response.json()["message"]


def test_first_promotion_rejects_unevaluated_critical_class(
    client, monkeypatch, tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    assert client.request(
        "PUT", f"{base}/critical-classes", headers=headers, json={"classes": [99999]}
    ).status_code == 200
    candidate = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]

    response = client.post(f"{base}/models/{candidate}/promote", headers=headers)

    assert response.status_code == 422
    assert "sem avaliacao" in response.json()["message"]


def test_admin_cannot_promote_model_from_another_company(
    client, monkeypatch, tmp_path,
):
    from tests.conftest import TestingSessionLocal
    from core.models import ModelVersion

    headers, first_company_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    first_base = f"/api/v1/companies/{first_company_id}/ml"
    version_id = _train_and_wait(client, f"{first_base}/train", headers=headers).json()["version_id"]
    with TestingSessionLocal() as session:
        user = session.query(Usuario).one()
        user.papel = "admin"
        other = _empresa(
            nome_empresa="Outra empresa ML", cnpj_cpf="99888777000166",
            api_key="api-key-outra-empresa", cod_dominio=8102,
        )
        session.add(other)
        session.commit()
        second_company_id = other.id
        refreshed_headers = _auth_headers(user)

    response = client.post(
        f"/api/v1/companies/{second_company_id}/ml/models/{version_id}/promote",
        headers=refreshed_headers,
    )

    assert response.status_code == 422
    with TestingSessionLocal() as session:
        assert session.get(ModelVersion, version_id).status == "candidate"


def test_candidate_evaluation_becomes_stale_when_active_changes(
    client, monkeypatch, tmp_path,
):
    headers, empresa_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    base = f"/api/v1/companies/{empresa_id}/ml"
    first = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    second = _train_and_wait(client, f"{base}/train", headers=headers).json()["version_id"]
    assert client.post(f"{base}/models/{first}/promote", headers=headers).status_code == 200

    response = client.post(f"{base}/models/{second}/promote", headers=headers)

    assert response.status_code == 422
    assert "desatualizada" in response.json()["message"]
