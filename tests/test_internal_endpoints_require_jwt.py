from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import Usuario


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
        "nome": "Ana Admin",
        "login": "ana.admin",
        "email": "ana.admin@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "admin",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


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


def test_internal_endpoint_rejects_request_without_jwt(client):
    response = client.get("/api/v1/admin/users")

    assert response.status_code in (401, 403)


def test_internal_endpoint_rejects_api_key_without_jwt(client):
    response = client.get(
        "/api/v1/admin/users",
        headers={"X-API-Key": "api-key-auth"},
    )

    assert response.status_code in (401, 403)


def test_internal_endpoint_accepts_valid_jwt(client):
    from tests.conftest import TestingSessionLocal

    admin = _usuario()
    with TestingSessionLocal() as session:
        session.add(admin)
        session.commit()
        session.refresh(admin)
        headers = _auth_headers(admin)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["login"] == "ana.admin"


def test_legacy_api_key_endpoint_keeps_accepting_api_key(client, empresa_criada):
    response = client.get(
        f"/api/v1/companies/{empresa_criada['id']}/transactions",
        headers={"X-API-Key": empresa_criada["api_key"]},
    )

    assert response.status_code == 200
    assert response.json() == []
