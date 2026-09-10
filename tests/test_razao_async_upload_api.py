from pathlib import Path

import pytest

from api.main import app
from api.routes.razao import get_razao_storage
from core.models import AuditEvent, LoteImportacaoRazao
from core.razao_storage import RazaoStorage
from core.razao_storage import InsufficientCapacity, UploadTooLarge
from tests.conftest import TestingSessionLocal
from tests.test_razao_import_api import (
    _auth_headers,
    _seed_user_company_and_catalog,
    _upload_file_with_metadata,
)


@pytest.fixture(autouse=True)
def private_upload_storage(client, tmp_path):
    storage = RazaoStorage(
        tmp_path / "uploads",
        max_bytes=5_000_000,
        min_free_bytes=0,
        min_free_ratio=0,
        sessions=TestingSessionLocal,
    )
    app.dependency_overrides[get_razao_storage] = lambda: storage
    yield storage


def test_new_upload_is_queued_without_accounting_in_http(client, monkeypatch):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")
    monkeypatch.setattr(
        "core.razao_importer.import_razao",
        lambda *args, **kwargs: pytest.fail("HTTP executou a contabilizacao"),
    )

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file_with_metadata("22.333.444/0001-55"),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 202, response.text
    assert response.headers["Retry-After"] == "3"
    assert response.json()["status"] == "queued"
    assert response.json()["status_url"].endswith(
        f"/companies/{empresa_id}/razao/lotes/{response.json()['lote_id']}"
    )
    assert set(response.json()) == {"lote_id", "status", "status_url"}
    with TestingSessionLocal() as session:
        lote = session.query(LoteImportacaoRazao).one()
        assert lote.total_linhas is None
        assert session.query(AuditEvent).one().event_type == "ledger.import_received"


@pytest.mark.parametrize(
    ("status", "expected_status"),
    [("queued", 202), ("processing", 202), ("completed", 200),
     ("completed_with_warnings", 200), ("failed", 409)],
)
def test_duplicate_upload_reuses_lote_by_status(
    client, private_upload_storage, status, expected_status
):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")
    headers = _auth_headers(usuario)
    first = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file_with_metadata("22.333.444/0001-55"), headers=headers,
    )
    with TestingSessionLocal.begin() as session:
        session.get(LoteImportacaoRazao, first.json()["lote_id"]).status = status

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file_with_metadata("22.333.444/0001-55"), headers=headers,
    )

    assert response.status_code == expected_status
    assert response.json()["lote_id"] == first.json()["lote_id"]
    assert response.json()["status"] == status
    if expected_status == 202:
        assert response.headers["Retry-After"] == "3"
    if status == "failed":
        assert response.json()["retry_url"].endswith(
            f"/companies/{empresa_id}/razao/lotes/{first.json()['lote_id']}/retry"
        )
    assert len([p for p in Path(private_upload_storage._root).iterdir()
                if p.is_dir()]) == 1


@pytest.mark.parametrize(
    ("error", "status_code", "message"),
    [(UploadTooLarge(), 413, "Upload excede o limite permitido."),
     (InsufficientCapacity(), 507, "Capacidade temporária indisponível.")],
)
def test_storage_admission_errors_are_safe_and_create_no_lote(
    client, private_upload_storage, error, status_code, message, monkeypatch
):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    def reject(_chunks):
        raise error

    monkeypatch.setattr(private_upload_storage, "admit", reject)
    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file_with_metadata("22.333.444/0001-55"),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == status_code
    assert response.json()["message"] == message
    assert "/" not in str(response.json()["details"])
    with TestingSessionLocal() as session:
        assert session.query(LoteImportacaoRazao).count() == 0


def test_async_upload_contract_is_published_in_openapi(client):
    app.openapi_schema = None
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/companies/{company_id}/razao/import"
    ]["post"]
    assert operation["responses"]["202"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/ImportacaoRazaoResponse")
    assert {"200", "202", "409", "413", "507"} <= set(operation["responses"])
