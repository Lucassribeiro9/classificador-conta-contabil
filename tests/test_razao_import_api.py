from datetime import datetime, timedelta, timezone
from io import BytesIO

import jwt
import pytest
from openpyxl import Workbook
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
        "nome": "Olivia Operadora",
        "login": "olivia.operadora",
        "email": "olivia.operadora@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Razao API LTDA",
        "cnpj_cpf": "22333444000155",
        "api_key": "api-key-razao-api",
        "cod_dominio": 9301,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(codigo: int) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
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


def _razao_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Conta:", "10046", "BCO. SANTANDER"])
    sheet.append(["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"])
    sheet.append(["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _upload_file(filename: str = "razao.xlsx") -> dict:
    return {
        "file": (
            filename,
            _razao_xlsx(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _seed_user_company_and_catalog(permissao: str = "operacao"):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )
    with TestingSessionLocal() as session:
        session.add_all([usuario, _conta(10046), _conta(20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        return usuario, empresa.id


def test_user_with_operacao_permission_imports_razao_and_receives_summary(client):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "lote_id": 1,
        "status": "completed",
        "total_linhas": 1,
        "total_importadas": 1,
        "total_invalidas": 0,
        "warnings": [],
    }


def test_successful_razao_import_creates_audit_event_with_counters(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.imported"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.resource_id == str(response.json()["lote_id"])
        assert event.metadata_json["total_linhas"] == 1
        assert event.metadata_json["total_importadas"] == 1
        assert event.metadata_json["total_invalidas"] == 0
        assert event.metadata_json["warnings"] == []
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert "Pagamento fornecedor" not in str(event.metadata_json)


def test_duplicate_razao_file_hash_creates_failed_audit_event(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("operacao")
    headers = _auth_headers(usuario)

    first_response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=headers,
    )
    second_response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "Arquivo ja importado com sucesso para esta empresa."

    with TestingSessionLocal() as session:
        events = session.query(AuditEvent).order_by(AuditEvent.id).all()
        assert [event.event_type for event in events] == [
            "ledger.imported",
            "ledger.import_failed",
        ]
        failed_event = events[-1]
        assert failed_event.user_id == usuario.id
        assert failed_event.empresa_id == empresa_id
        assert failed_event.metadata_json["file_hash"].startswith("sha256:")
        assert failed_event.metadata_json["error_type"] == "RazaoImportError"
        assert failed_event.metadata_json["reason"] == "duplicate_file_hash"
        assert "Traceback" not in failed_event.metadata_json["error"]


def test_user_with_admin_empresa_permission_imports_razao(client):
    usuario, empresa_id = _seed_user_company_and_catalog("admin_empresa")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["total_importadas"] == 1


def test_user_with_leitura_permission_cannot_import_razao(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("leitura")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Permissão insuficiente"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.import_denied"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert event.metadata_json["reason"] == "insufficient_permission"


def test_user_without_company_link_cannot_import_razao(client):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, _conta(10046), _conta(20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        headers = _auth_headers(usuario)
        empresa_id = empresa.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.import_denied"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert event.metadata_json["reason"] == "access_denied"
        assert "Pagamento fornecedor" not in str(event.metadata_json)


def test_razao_import_rejects_non_xlsx_file(client):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files={"file": ("razao.csv", b"Conta:,10046", "text/csv")},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo deve ser .xlsx"


def test_razao_import_requires_jwt(client):
    _, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
    )

    assert response.status_code in (401, 403)
