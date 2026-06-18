from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends

from api.dependencies import DB_DEPENDENCY, get_current_user
from api.main import app
from core.audit import get_audit_user_id, record_audit_event
from core.config import settings
from core.models import AuditEvent, Usuario


def _install_probe_route() -> None:
    if any(route.path == "/__tests__/audit-context" for route in app.routes):
        return

    @app.post("/__tests__/audit-context")
    def audit_context_probe(
        _current_user: Usuario = Depends(get_current_user),
        db=DB_DEPENDENCY,
    ):
        event = record_audit_event(
            db,
            event_type="audit.context.probe",
            metadata={"source": "request"},
        )
        db.commit()
        db.refresh(event)
        return {"event_id": event.id, "user_id": event.user_id}


_install_probe_route()


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
        "nome": "Ana Auditora",
        "login": "ana.auditora",
        "email": "ana.auditora@example.com",
        "senha_hash": "$argon2id$v=19$hash-de-teste",
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


def test_authenticated_request_injects_user_for_audit_event(client):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    with TestingSessionLocal() as session:
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
        headers = {"Authorization": f"Bearer {_access_token(usuario)}"}

    response = client.post("/__tests__/audit-context", headers=headers)

    assert response.status_code == 200
    assert response.json()["user_id"] == usuario.id
    assert get_audit_user_id() is None

    with TestingSessionLocal() as session:
        saved = session.query(AuditEvent).one()
        assert saved.event_type == "audit.context.probe"
        assert saved.user_id == usuario.id
        assert saved.metadata_json == {"source": "request"}


def test_audit_event_without_request_context_is_anonymous(setup_db):
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        event = record_audit_event(
            session,
            event_type="system.job.completed",
            metadata={"source": "background"},
        )
        session.commit()
        session.refresh(event)

    assert event.user_id is None

    with TestingSessionLocal() as session:
        saved = session.query(AuditEvent).one()
        assert saved.event_type == "system.job.completed"
        assert saved.user_id is None
        assert saved.metadata_json == {"source": "background"}
