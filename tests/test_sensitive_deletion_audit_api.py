from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import AuditEvent, Empresa, LoteImportacaoRazao, Usuario


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


def _admin() -> Usuario:
    return Usuario(
        nome="Ana Admin",
        login="ana.admin",
        email="ana.admin@example.com",
        senha_hash=password_hash.hash("senha-segura-123"),
        papel="admin",
        is_active=True,
    )


def _empresa() -> Empresa:
    return Empresa(
        nome_empresa="Empresa Sensivel LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-sensitive",
        cod_dominio=8801,
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


def _seed_admin_and_company():
    from tests.conftest import TestingSessionLocal

    admin = _admin()
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([admin, empresa])
        session.commit()
        session.refresh(admin)
        session.refresh(empresa)
        return admin, empresa.id


def _seed_admin_company_and_lote():
    from tests.conftest import TestingSessionLocal

    admin = _admin()
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=admin,
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
        total_linhas=10,
        total_importadas=8,
        total_invalidas=2,
        warnings_metadata={"warnings": []},
    )
    with TestingSessionLocal() as session:
        session.add_all([admin, empresa, lote])
        session.commit()
        session.refresh(admin)
        session.refresh(empresa)
        session.refresh(lote)
        return admin, empresa.id, lote.id


def test_admin_deletes_company_and_audits_original_name(client):
    from tests.conftest import TestingSessionLocal

    admin, empresa_id = _seed_admin_and_company()

    response = client.delete(
        f"/api/v1/admin/companies/{empresa_id}",
        headers=_auth_headers(admin),
    )

    assert response.status_code == 204

    with TestingSessionLocal() as session:
        assert session.get(Empresa, empresa_id) is None
        event = session.query(AuditEvent).one()
        assert event.event_type == "company.deleted"
        assert event.user_id == admin.id
        assert event.empresa_id is None
        assert event.resource_id == str(empresa_id)
        assert event.metadata_json == {
            "company_id": empresa_id,
            "nome_empresa": "Empresa Sensivel LTDA",
            "cnpj_cpf": "11222333000144",
            "cod_dominio": 8801,
        }


def test_admin_deletes_ledger_batch_and_audits_original_filename(client):
    from tests.conftest import TestingSessionLocal

    admin, empresa_id, lote_id = _seed_admin_company_and_lote()

    response = client.delete(
        f"/api/v1/admin/razao/lotes/{lote_id}",
        headers=_auth_headers(admin),
    )

    assert response.status_code == 204

    with TestingSessionLocal() as session:
        assert session.get(LoteImportacaoRazao, lote_id) is None
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.deleted"
        assert event.user_id == admin.id
        assert event.empresa_id == empresa_id
        assert event.resource_id == str(lote_id)
        assert event.metadata_json["lote_id"] == lote_id
        assert event.metadata_json["original_filename"] == "razao-janeiro.xlsx"
        assert event.metadata_json["file_hash"] == "sha256:abc123"
        assert event.metadata_json["status"] == "completed"
