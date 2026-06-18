from datetime import datetime, timezone

import jwt
import pytest
from fastapi import HTTPException
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes.auth import login_for_access_token
from api.schemas import LoginRequest
from core.config import settings
from core.database import Base
from core.models import AuditEvent, Usuario


password_hash = PasswordHash.recommended()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


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


def _usuario(password: str = "senha-segura-123", **overrides) -> Usuario:
    data = {
        "nome": "Ana Contadora",
        "login": "ana.contadora",
        "email": "ana.contadora@example.com",
        "senha_hash": password_hash.hash(password),
        "papel": "contador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def test_login_valid_returns_access_token_with_user_claims_and_12h_expiration(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    response = login_for_access_token(
        credentials=LoginRequest(login="ana.contadora", senha="senha-segura-123"),
        db=session,
    )

    payload = jwt.decode(
        response.access_token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    assert response.token_type == "bearer"
    assert response.expires_in == 12 * 60 * 60
    assert "refresh_token" not in response.model_dump()
    assert payload["sub"] == str(usuario.id)
    assert payload["role"] == "contador"
    assert payload["type"] == "access"
    assert (expires_at - issued_at).total_seconds() == 12 * 60 * 60


def test_login_valid_creates_success_audit_event_without_password(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    login_for_access_token(
        credentials=LoginRequest(login="ana.contadora", senha="senha-segura-123"),
        db=session,
    )

    event = session.query(AuditEvent).one()
    assert event.event_type == "auth.login_success"
    assert event.user_id == usuario.id
    assert event.metadata_json == {"login": "ana.contadora"}
    assert "senha" not in event.metadata_json
    assert "password" not in event.metadata_json


def test_login_accepts_email_as_identifier(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    response = login_for_access_token(
        credentials=LoginRequest(
            login="ana.contadora@example.com",
            senha="senha-segura-123",
        ),
        db=session,
    )

    payload = jwt.decode(
        response.access_token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    assert payload["sub"] == str(usuario.id)


def test_login_rejects_invalid_password_without_leaking_user_existence(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        login_for_access_token(
            credentials=LoginRequest(login="ana.contadora", senha="senha-errada"),
            db=session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Credenciais inválidas"

    event = session.query(AuditEvent).one()
    assert event.event_type == "auth.login_failed"
    assert event.user_id == usuario.id
    assert event.metadata_json == {"login": "ana.contadora", "reason": "invalid_credentials"}
    assert "senha" not in event.metadata_json
    assert "password" not in event.metadata_json


def test_login_rejects_missing_user_without_leaking_user_existence(session):
    with pytest.raises(HTTPException) as exc_info:
        login_for_access_token(
            credentials=LoginRequest(login="ninguem@example.com", senha="senha-qualquer"),
            db=session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Credenciais inválidas"

    event = session.query(AuditEvent).one()
    assert event.event_type == "auth.login_failed"
    assert event.user_id is None
    assert event.metadata_json == {"login": "ninguem@example.com", "reason": "invalid_credentials"}
    assert "senha" not in event.metadata_json
    assert "password" not in event.metadata_json


def test_login_rejects_inactive_user(session):
    session.add(_usuario(is_active=False))
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        login_for_access_token(
            credentials=LoginRequest(login="ana.contadora", senha="senha-segura-123"),
            db=session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Usuário inativo"


def test_auth_login_route_is_registered():
    from api.main import app

    routes = {(route.path, next(iter(route.methods))) for route in app.routes}

    assert ("/api/v1/auth/login", "POST") in routes
