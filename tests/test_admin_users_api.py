from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import AuditEvent, Usuario


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


def test_admin_creates_user_with_allowed_role_without_exposing_password(client):
    admin = _usuario()

    # Seed through the same test DB used by the API dependency override.
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(admin)
        session.commit()
        session.refresh(admin)
        headers = _auth_headers(admin)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "nome": "Bruno Operador",
            "login": "bruno.operador",
            "email": "bruno.operador@example.com",
            "senha": "senha-operador-123",
            "papel": "operador",
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "bruno.operador"
    assert data["papel"] == "operador"
    assert data["is_active"] is True
    assert "senha" not in data
    assert "senha_hash" not in data

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()

    assert event.event_type == "user.created"
    assert event.user_id == admin.id
    assert event.empresa_id is None
    assert event.resource_id == str(data["id"])
    assert event.metadata_json == {
        "target_user_id": data["id"],
        "target_login": "bruno.operador",
        "target_email": "bruno.operador@example.com",
        "target_role": "operador",
    }
    assert "senha" not in event.metadata_json
    assert "senha_hash" not in event.metadata_json
    assert "token" not in event.metadata_json


def test_non_admin_cannot_create_user(client):
    contador = _usuario(
        nome="Caio Contador",
        login="caio.contador",
        email="caio.contador@example.com",
        papel="contador",
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(contador)
        session.commit()
        session.refresh(contador)
        headers = _auth_headers(contador)

    response = client.post(
        "/api/v1/admin/users",
        json={
            "nome": "Bruno Operador",
            "login": "bruno.operador",
            "email": "bruno.operador@example.com",
            "senha": "senha-operador-123",
            "papel": "operador",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso restrito a administradores"


def test_admin_lists_users_without_password_hash(client):
    admin = _usuario()
    operador = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add_all([admin, operador])
        session.commit()
        session.refresh(admin)
        headers = _auth_headers(admin)

    response = client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    users = response.json()
    assert {user["login"] for user in users} == {"ana.admin", "bruno.operador"}
    assert all("senha_hash" not in user for user in users)
    assert all("senha" not in user for user in users)


def test_admin_deactivates_and_reactivates_user(client):
    admin = _usuario()
    operador = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add_all([admin, operador])
        session.commit()
        session.refresh(admin)
        session.refresh(operador)
        headers = _auth_headers(admin)
        operador_id = operador.id

    deactivate_response = client.patch(
        f"/api/v1/admin/users/{operador_id}/deactivate",
        headers=headers,
    )
    activate_response = client.patch(
        f"/api/v1/admin/users/{operador_id}/activate",
        headers=headers,
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()

    assert event.event_type == "user.deactivated"
    assert event.user_id == admin.id
    assert event.empresa_id is None
    assert event.resource_id == str(operador_id)
    assert event.metadata_json == {
        "target_user_id": operador_id,
        "target_login": "bruno.operador",
        "old_is_active": True,
        "new_is_active": False,
    }


def test_admin_resets_user_password_without_exposing_secret(client):
    admin = _usuario()
    operador = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
        senha_hash=password_hash.hash("senha-antiga-123"),
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add_all([admin, operador])
        session.commit()
        session.refresh(admin)
        session.refresh(operador)
        headers = _auth_headers(admin)
        operador_id = operador.id

    response = client.patch(
        f"/api/v1/admin/users/{operador_id}/reset-password",
        json={"senha": "senha-nova-456"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == operador_id
    assert data["login"] == "bruno.operador"
    assert "senha" not in data
    assert "senha_hash" not in data

    old_login = client.post(
        "/api/v1/auth/login",
        json={"login": "bruno.operador", "senha": "senha-antiga-123"},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"login": "bruno.operador", "senha": "senha-nova-456"},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200

    with TestingSessionLocal() as session:
        event = (
            session.query(AuditEvent)
            .filter(AuditEvent.event_type == "user.password_reset")
            .one()
        )

    assert event.user_id == admin.id
    assert event.empresa_id is None
    assert event.resource_id == str(operador_id)
    assert event.metadata_json == {
        "target_user_id": operador_id,
        "target_login": "bruno.operador",
    }
    assert "senha" not in event.metadata_json
    assert "senha_hash" not in event.metadata_json
    assert "password" not in event.metadata_json
    assert "token" not in event.metadata_json


def test_non_admin_cannot_reset_user_password(client):
    contador = _usuario(
        nome="Caio Contador",
        login="caio.contador",
        email="caio.contador@example.com",
        papel="contador",
    )
    operador = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add_all([contador, operador])
        session.commit()
        session.refresh(contador)
        session.refresh(operador)
        headers = _auth_headers(contador)
        operador_id = operador.id

    response = client.patch(
        f"/api/v1/admin/users/{operador_id}/reset-password",
        json={"senha": "senha-nova-456"},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso restrito a administradores"
