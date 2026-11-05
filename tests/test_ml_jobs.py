"""Contrato público da fila de ML."""

from core.ml_jobs import claim_next_ml_job, enqueue_ml_job
from datetime import datetime, timedelta
from core.models import Empresa, MLJob, Usuario, UsuarioEmpresaPermissao
from tests.conftest import TestingSessionLocal
from tests.test_ml_train_endpoint import _seed_company_with_razao
from tests.test_movimentos_operacionais_api import (
    _auth_headers as operational_headers,
    _seed_operational_lote_with_movements,
)
from core.ml_worker import MLWorker


def test_reenvio_idempotente_reusa_job_sem_criar_outro(setup_db):
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Empresa Jobs",
            api_key="jobs-key",
            cnpj_cpf="12345678000199",
            cod_dominio=506,
        )
        session.add(company)
        session.commit()
        first = enqueue_ml_job(
            session, company_id=company.id, kind="train",
            idempotency_key="treino-1", payload={},
        )
        session.commit()
        second = enqueue_ml_job(
            session, company_id=company.id, kind="train",
            idempotency_key="treino-1", payload={},
        )
        assert second.id == first.id
        assert second.status == "queued"


def test_claim_nao_executa_dois_jobs_da_mesma_empresa(setup_db):
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Empresa Claims", api_key="claims-key",
            cnpj_cpf="12345678000200", cod_dominio=507,
        )
        session.add(company)
        session.flush()
        ids = [enqueue_ml_job(
            session, company_id=company.id, kind="train",
            idempotency_key=f"treino-{n}", payload={},
        ).id for n in (1, 2)]
        session.commit()

    first = claim_next_ml_job(TestingSessionLocal, worker_id="worker-a")
    second = claim_next_ml_job(TestingSessionLocal, worker_id="worker-b")
    assert first is not None and first.id == ids[0]
    assert second is None


def test_lease_expirada_e_recuperada_sem_aceitar_worker_antigo(setup_db, tmp_path):
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Empresa Recovery", api_key="recovery-key",
            cnpj_cpf="12345678000201", cod_dominio=508,
        )
        session.add(company)
        session.flush()
        job_id = enqueue_ml_job(
            session, company_id=company.id, kind="train",
            idempotency_key="recovery-1", payload={},
        ).id
        session.commit()
    start = datetime(2026, 1, 1)
    old = claim_next_ml_job(TestingSessionLocal, worker_id="old", now=start, lease_seconds=5)
    new = claim_next_ml_job(
        TestingSessionLocal, worker_id="new",
        now=start + timedelta(seconds=6), lease_seconds=5,
    )
    assert old is not None and new is not None
    assert old.id == new.id == job_id
    assert old.lease_token != new.lease_token
    MLWorker(TestingSessionLocal, worker_id="old", model_dir=tmp_path)._finish_failure(old, "processing_error")
    with TestingSessionLocal() as session:
        job = session.get(MLJob, job_id)
        assert job.status == "running"
        assert job.lease_token == new.lease_token


def test_falha_transitoria_tenta_de_novo_sem_publicar_parcial(setup_db, tmp_path):
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Empresa Retry", api_key="retry-key",
            cnpj_cpf="12345678000202", cod_dominio=509,
        )
        session.add(company)
        session.flush()
        job_id = enqueue_ml_job(
            session, company_id=company.id, kind="classify",
            idempotency_key="retry-1", payload={"inputs": []},
        ).id
        session.commit()
    worker = MLWorker(TestingSessionLocal, worker_id="retry-worker", model_dir=tmp_path)
    calls = 0

    def classify(_session, _job):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("falha transitória simulada")
        return {"results": []}

    worker._classify = classify
    assert worker.run_once()
    with TestingSessionLocal() as session:
        job = session.get(MLJob, job_id)
        assert job.status == "queued"
        assert job.result is None
        assert job.attempts == 1
    assert worker.run_once()
    with TestingSessionLocal() as session:
        job = session.get(MLJob, job_id)
        assert job.status == "completed"
        assert job.result == {"results": []}
        assert job.attempts == 2


def test_treino_retorna_job_sem_treinar_na_requisicao(client, monkeypatch, tmp_path):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "train-506"
    response = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["job_id"] > 0
    assert not list(tmp_path.rglob("*.joblib"))


def test_classificacao_canonica_retorna_job(client):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "classify-506"
    payload = {"historico": "Pagamento de fornecedor", "conta_origem": 1001, "direcao": "debito"}
    response = client.post(
        f"/api/v1/companies/{company_id}/ml/classification",
        headers=headers, json=payload,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_chave_reusada_com_outro_payload_e_rejeitada(client):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "conflict-506"
    url = f"/api/v1/companies/{company_id}/ml/classification"
    first = {"historico": "Pagamento A", "conta_origem": 1001, "direcao": "debito"}
    second = {"historico": "Pagamento B", "conta_origem": 1001, "direcao": "debito"}
    accepted = client.post(url, headers=headers, json=first)
    conflict = client.post(url, headers=headers, json=second)
    assert accepted.status_code == 202
    assert conflict.status_code == 409


def test_classificacao_operacional_retorna_job(client):
    user, company_id, _ = _seed_operational_lote_with_movements(permissao="operacao")
    headers = operational_headers(user)
    headers["Idempotency-Key"] = "movimentos-506"
    response = client.post(
        f"/api/v1/companies/{company_id}/movimentos-operacionais/classificar",
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_job_pode_ser_consultado_e_cancelado_pela_empresa(client):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "cancel-506"
    queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
    job_id = queued.json()["job_id"]
    url = f"/api/v1/companies/{company_id}/ml/jobs/{job_id}"
    before = client.get(url, headers=headers)
    assert before.status_code == 200
    assert before.json()["result"] is None
    cancelled = client.post(f"{url}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert client.get(url, headers=headers).json()["status"] == "cancelled"


def test_empresa_autorizada_nao_ve_job_de_outra_empresa(client):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "isolation-506"
    queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
    job_id = queued.json()["job_id"]
    with TestingSessionLocal() as session:
        other = Empresa(
            nome_empresa="Outra Empresa Jobs", api_key="other-jobs-key",
            cnpj_cpf="12345678000203", cod_dominio=510,
        )
        session.add(other)
        session.flush()
        user_id = session.query(Usuario.id).one()[0]
        session.add(UsuarioEmpresaPermissao(
            usuario_id=user_id, empresa_id=other.id, permissao="operacao",
        ))
        other_id = other.id
        session.commit()
    response = client.get(
        f"/api/v1/companies/{other_id}/ml/jobs/{job_id}", headers=headers,
    )
    assert response.status_code == 404


def test_retry_manual_reenfileira_somente_job_falho(client, tmp_path):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057],
    )
    headers["Idempotency-Key"] = "manual-retry-506"
    queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
    url = queued.json()["status_url"]
    assert client.post(f"{url}/retry", headers=headers).status_code == 409
    assert MLWorker(TestingSessionLocal, worker_id="failed-train", model_dir=tmp_path).run_once()
    failed = client.get(url, headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["error_code"] == "insufficient_dataset"
    retried = client.post(f"{url}/retry", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
    assert retried.json()["attempts"] == 0


def test_worker_treina_e_publica_candidato_apos_conclusao(client, monkeypatch, tmp_path):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "worker-train-506"
    queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
    assert queued.status_code == 202
    worker = MLWorker(TestingSessionLocal, worker_id="test-worker", model_dir=tmp_path)
    assert worker.run_once() is True
    response = client.get(queued.json()["status_url"], headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"]["status"] == "candidate"
    assert response.json()["result"]["version_id"] > 0


def test_falha_apos_artefato_nao_deixa_modelo_parcial(client, monkeypatch, tmp_path):
    headers, company_id = _seed_company_with_razao(
        permissao="operacao", targets=[50057, 70001] * 5,
    )
    headers["Idempotency-Key"] = "artifact-failure-506"
    queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)

    def fail_after_artifact(*_args, **_kwargs):
        raise RuntimeError("falha simulada apos escrever artefato")

    monkeypatch.setattr("core.model_versions.record_audit_event", fail_after_artifact)
    worker = MLWorker(TestingSessionLocal, worker_id="artifact-failure", model_dir=tmp_path)
    assert worker.run_once()
    status = client.get(queued.json()["status_url"], headers=headers).json()
    assert status["status"] == "queued"
    assert status["result"] is None
    assert not list(tmp_path.rglob("*.joblib"))


def test_worker_classifica_com_modelo_ativo_sem_resultado_parcial(client, tmp_path):
    from core.config import settings

    headers, company_id = _seed_company_with_razao(
        permissao="admin_empresa", targets=[50057, 70001] * 5,
    )
    old_dir = settings.MODEL_DIR
    settings.MODEL_DIR = str(tmp_path)
    try:
        worker = MLWorker(TestingSessionLocal, worker_id="worker-classify", model_dir=tmp_path)
        headers["Idempotency-Key"] = "train-for-classify-506"
        queued = client.post(f"/api/v1/companies/{company_id}/ml/train", headers=headers)
        assert worker.run_once()
        trained = client.get(queued.json()["status_url"], headers=headers).json()
        version_id = trained["result"]["version_id"]
        promoted = client.post(
            f"/api/v1/companies/{company_id}/ml/models/{version_id}/promote",
            headers=headers,
        )
        assert promoted.status_code == 200
        headers["Idempotency-Key"] = "classify-after-train-506"
        payload = {"historico": "Pagamento de fornecedor", "conta_origem": 1001, "direcao": "debito"}
        queued = client.post(
            f"/api/v1/companies/{company_id}/ml/classification",
            headers=headers, json=payload,
        )
        assert client.get(queued.json()["status_url"], headers=headers).json()["result"] is None
        assert worker.run_once()
        completed = client.get(queued.json()["status_url"], headers=headers).json()
        assert completed["status"] == "completed"
        assert completed["result"]["model_version_id"] == version_id
        assert completed["result"]["quantidade_processada"] == 1
    finally:
        settings.MODEL_DIR = old_dir
