from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import AuditEvent, Empresa, Usuario


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


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Auditada LTDA",
        "cnpj_cpf": "12345678000199",
        "cod_dominio": 1001,
        "api_key": "api-key-audit",
        "is_active": True,
    }
    data.update(overrides)
    return Empresa(**data)


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


def _seed_audit_context():
    from tests.conftest import TestingSessionLocal

    admin = _usuario()
    empresa = _empresa()
    now = datetime(2026, 6, 26, 10, 30, 0)
    events = [
        AuditEvent(
            timestamp=now - timedelta(minutes=10),
            event_type="auth.login.success",
            user_id=None,
            empresa_id=None,
            resource_id=None,
            metadata_json={"reason": "valid_credentials"},
        ),
        AuditEvent(
            timestamp=now,
            event_type="ledger.imported",
            user_id=None,
            empresa_id=None,
            resource_id="42",
            metadata_json={"total_importadas": 12},
        ),
    ]

    with TestingSessionLocal() as session:
        session.add_all([admin, empresa])
        session.flush()
        for event in events:
            event.user_id = admin.id
            if event.event_type == "ledger.imported":
                event.empresa_id = empresa.id
        session.add_all(events)
        session.commit()
        session.refresh(admin)
        session.refresh(empresa)
        return admin, empresa.id


def _seed_filtered_audit_context():
    from tests.conftest import TestingSessionLocal

    admin = _usuario()
    contador = _usuario(
        nome="Caio Contador",
        login="caio.contador",
        email="caio.contador@example.com",
        papel="contador",
    )
    empresa_a = _empresa()
    empresa_b = _empresa(
        nome_empresa="Outra Empresa LTDA",
        cnpj_cpf="98765432000199",
        cod_dominio=1002,
        api_key="api-key-outra",
    )

    with TestingSessionLocal() as session:
        session.add_all([admin, contador, empresa_a, empresa_b])
        session.flush()
        session.add_all(
            [
                AuditEvent(
                    timestamp=datetime(2026, 6, 20, 9, 0, 0),
                    event_type="ledger.imported",
                    user_id=admin.id,
                    empresa_id=empresa_a.id,
                    resource_id="1",
                    metadata_json={"total_importadas": 10},
                ),
                AuditEvent(
                    timestamp=datetime(2026, 6, 21, 9, 0, 0),
                    event_type="feedback.created",
                    user_id=contador.id,
                    empresa_id=empresa_a.id,
                    resource_id="2",
                    metadata_json={"lancamento_id": 99},
                ),
                AuditEvent(
                    timestamp=datetime(2026, 6, 22, 9, 0, 0),
                    event_type="ledger.imported",
                    user_id=admin.id,
                    empresa_id=empresa_b.id,
                    resource_id="3",
                    metadata_json={"total_importadas": 20},
                ),
            ]
        )
        session.commit()
        session.refresh(admin)
        session.refresh(contador)
        session.refresh(empresa_a)
        return admin, contador, empresa_a.id


def test_admin_lists_audit_events_paginated_newest_first(client):
    admin, empresa_id = _seed_audit_context()

    response = client.get(
        "/api/v1/admin/audit-events",
        params={"page": 1, "limit": 1},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["limit"] == 1
    assert data["has_next"] is True
    assert len(data["items"]) == 1
    assert data["items"][0]["event_type"] == "ledger.imported"
    assert data["items"][0]["empresa_id"] == empresa_id
    assert data["items"][0]["resource_id"] == "42"
    assert data["items"][0]["metadata"] == {"total_importadas": 12}


def test_admin_filters_audit_events_by_user_company_event_and_period(client):
    admin, contador, empresa_id = _seed_filtered_audit_context()

    response = client.get(
        "/api/v1/admin/audit-events",
        params={
            "user_id": contador.id,
            "empresa_id": empresa_id,
            "event_type": "feedback.created",
            "data_inicio": date(2026, 6, 21).isoformat(),
            "data_fim": date(2026, 6, 21).isoformat(),
        },
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["has_next"] is False
    assert [item["event_type"] for item in data["items"]] == ["feedback.created"]
    assert data["items"][0]["user_id"] == contador.id
    assert data["items"][0]["empresa_id"] == empresa_id
    assert data["items"][0]["metadata"] == {"lancamento_id": 99}


def test_non_admin_cannot_list_audit_events(client):
    _admin, contador, _empresa_id = _seed_filtered_audit_context()

    response = client.get(
        "/api/v1/admin/audit-events",
        headers=_auth_headers(contador),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso restrito a administradores"
