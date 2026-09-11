from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from api.main import app
from api.routes.razao import get_razao_storage
from core.models import AuditEvent, LoteImportacaoRazao, TentativaImportacaoRazao
from core.razao_storage import RazaoStorage, TemporaryFileBusy
from tests.conftest import TestingSessionLocal
from tests.test_razao_import_api import (
    _auth_headers,
    _seed_razao_lote_with_lancamento,
    _seed_user_company_and_catalog,
)


@pytest.fixture(autouse=True)
def private_upload_storage(client, tmp_path):
    storage = RazaoStorage(
        tmp_path / "retry-uploads",
        max_bytes=4096,
        min_free_bytes=0,
        min_free_ratio=0,
        sessions=TestingSessionLocal,
    )
    app.dependency_overrides[get_razao_storage] = lambda: storage
    yield storage


def test_user_with_read_access_gets_real_razao_lote_progress(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    started_at = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "processing"
        lote.total_linhas = None
        lote.linhas_processadas = 37
        lote.total_importadas = 35
        lote.total_invalidas = 2
        lote.warnings_total = 4
        lote.warnings_metadata = {
            "totals_by_code": {"conta_invalida": 2, "saldo_divergente": 2}
        }
        lote.attempt_count = 1
        lote.heartbeat_at = started_at
        session.add(
            TentativaImportacaoRazao(
                lote_id=lote_id,
                numero=1,
                started_at=started_at,
            )
        )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lote_id"] == lote_id
    assert body["empresa_id"] == empresa_id
    assert body["status"] == "processing"
    assert body["total_linhas"] is None
    assert body["linhas_processadas"] == 37
    assert body["total_importadas"] == 35
    assert body["total_invalidas"] == 2
    assert body["warnings_total"] == 4
    assert body["warnings_summary"] == {
        "conta_invalida": 2,
        "saldo_divergente": 2,
    }
    assert body["attempt_count"] == 1
    assert body["tentativas"] == [
        {
            "numero": 1,
            "started_at": "2026-09-11T12:00:00",
            "finished_at": None,
            "resultado": None,
        }
    ]
    assert body["heartbeat_at"] == "2026-09-11T12:00:00"
    assert "progress_percent" not in body
    assert "error_code" not in body


def test_operator_retries_failed_lote_and_preserves_attempt_history(
    client, private_upload_storage
):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")
    failed_at = datetime(2026, 9, 11, 12, 30, tzinfo=timezone.utc)
    with private_upload_storage.admit([b"synthetic-xlsx"]) as upload:
        with TestingSessionLocal.begin() as session:
            lote = LoteImportacaoRazao(
                empresa_id=empresa_id,
                usuario_id=usuario.id,
                original_filename="razao-sanitizado.xlsx",
                file_hash=upload.file_hash,
                status="failed",
                total_linhas=100,
                linhas_processadas=80,
                total_importadas=75,
                total_invalidas=5,
                warnings_total=3,
                warnings_metadata={"totals_by_code": {"conta_invalida": 3}},
                attempt_count=1,
                error_code="invalid_ledger",
                error_message="Falha segura.",
                error_request_id="request-safe",
                failed_at=failed_at,
            )
            session.add(lote)
            upload.bind(session, lote)
            session.add(
                TentativaImportacaoRazao(
                    lote=lote,
                    numero=1,
                    started_at=failed_at,
                    finished_at=failed_at,
                    resultado="failed",
                )
            )
            lote_id = lote.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/retry",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 202
    assert response.headers["Retry-After"] == "3"
    assert response.json() == {
        "lote_id": lote_id,
        "status": "queued",
        "status_url": f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}",
    }
    with TestingSessionLocal() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "queued"
        assert lote.total_linhas is None
        assert lote.linhas_processadas == 0
        assert lote.total_importadas == 0
        assert lote.total_invalidas == 0
        assert lote.warnings_total == 0
        assert lote.warnings_metadata == {"totals_by_code": {}}
        assert lote.error_code is None
        assert lote.error_message is None
        assert lote.error_request_id is None
        assert lote.failed_at is None
        assert lote.attempt_count == 1
        assert [attempt.numero for attempt in lote.tentativas] == [1]
        event = session.query(AuditEvent).filter_by(
            event_type="razao.job.manual_retry"
        ).one()
        assert event.user_id == usuario.id
        assert event.metadata_json == {"attempt_count": 1}


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_active_lote_does_not_expose_derived_results(client, status):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = status
        lote.linhas_processadas = 1

    lancamentos = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/lancamentos",
        headers=_auth_headers(usuario),
    )
    fechamentos = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        headers=_auth_headers(usuario),
    )

    assert lancamentos.status_code == 409
    assert fechamentos.status_code == 409
    assert lancamentos.json()["message"] == "Resultados ainda não estão disponíveis"
    assert fechamentos.json()["message"] == "Resultados ainda não estão disponíveis"


def test_failed_lote_status_exposes_only_safe_correlated_error(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    failed_at = datetime(2026, 9, 11, 14, 0, tzinfo=timezone.utc)
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "failed"
        lote.error_code = "processing_failed"
        lote.error_message = "Falha temporária no processamento."
        lote.error_request_id = "request-correlated"
        lote.failed_at = failed_at

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error_code"] == "processing_failed"
    assert body["error_message"] == "Falha temporária no processamento."
    assert body["error_request_id"] == "request-correlated"
    assert body["failed_at"] == "2026-09-11T14:00:00"
    assert "traceback" not in str(body).lower()
    assert "path" not in str(body).lower()
    assert "file_hash" not in body
    assert "original_filename" not in body


def test_retry_returns_gone_when_failed_lote_file_is_unavailable(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="operacao"
    )
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "failed"
        lote.failed_at = datetime.now(timezone.utc)

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/retry",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 410
    assert response.json()["message"] == (
        "Arquivo temporário não está mais disponível"
    )


def test_concurrent_retry_returns_conflict(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="operacao"
    )
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "failed"
        lote.failed_at = datetime.now(timezone.utc)

    class BusyStorage:
        @contextmanager
        def retry_guard(self, _lote_id):
            raise TemporaryFileBusy()
            yield

    app.dependency_overrides[get_razao_storage] = BusyStorage
    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/retry",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Lote não está disponível para repetição"


def test_retry_rejects_non_failed_lote(client):
    operador, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="operacao"
    )
    conflict = client.post(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/retry",
        headers=_auth_headers(operador),
    )
    assert conflict.status_code == 409


def test_retry_rejects_read_only_user(client):
    leitura, leitura_empresa_id, leitura_lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    forbidden = client.post(
        f"/api/v1/companies/{leitura_empresa_id}/razao/lotes/{leitura_lote_id}/retry",
        headers=_auth_headers(leitura),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["message"] == "Permissão insuficiente"


def test_status_and_retry_contracts_are_published_in_openapi(client):
    app.openapi_schema = None
    paths = client.get("/openapi.json").json()["paths"]
    status_operation = paths["/api/v1/companies/{company_id}/razao/lotes/{lote_id}"][
        "get"
    ]
    retry_operation = paths[
        "/api/v1/companies/{company_id}/razao/lotes/{lote_id}/retry"
    ]["post"]

    assert "200" in status_operation["responses"]
    assert {"202", "409", "410"} <= set(retry_operation["responses"])
    assert status_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/RazaoLoteStatusResponse")
