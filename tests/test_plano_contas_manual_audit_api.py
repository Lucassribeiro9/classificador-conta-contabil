from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import AuditEvent, ContaContabil, Usuario


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


def _conta(**overrides) -> ContaContabil:
    data = {
        "codigo": 10046,
        "classificacao": "1.1.01.01.02.10046",
        "nome": "BCO. SANTANDER",
        "tipo": "A",
        "grau": 6,
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


def _seed_admin_and_account():
    from tests.conftest import TestingSessionLocal

    admin = _admin()
    conta = _conta()
    with TestingSessionLocal() as session:
        session.add_all([admin, conta])
        session.commit()
        session.refresh(admin)
        session.refresh(conta)
        return admin, conta.codigo


def test_admin_updates_financial_origin_flag_and_audits_change(client):
    from tests.conftest import TestingSessionLocal

    admin, codigo = _seed_admin_and_account()

    response = client.patch(
        f"/api/v1/admin/plano-contas/{codigo}/financial-origin",
        json={"is_financial_origin": True},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["codigo"] == codigo
    assert response.json()["is_financial_origin"] is True

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "account.updated"
        assert event.user_id == admin.id
        assert event.resource_id == str(codigo)
        assert event.metadata_json == {
            "field": "is_financial_origin",
            "old_value": False,
            "new_value": True,
        }


def test_admin_deactivates_account_and_audits_change(client):
    from tests.conftest import TestingSessionLocal

    admin, codigo = _seed_admin_and_account()

    response = client.patch(
        f"/api/v1/admin/plano-contas/{codigo}/deactivate",
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["codigo"] == codigo
    assert response.json()["is_active"] is False

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "account.deactivated"
        assert event.user_id == admin.id
        assert event.resource_id == str(codigo)
        assert event.metadata_json == {
            "field": "is_active",
            "old_value": True,
            "new_value": False,
        }
