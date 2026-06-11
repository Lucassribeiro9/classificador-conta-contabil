from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_current_user
from core.config import settings
from core.database import Base
from core.models import Usuario


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
    settings.JWT_SECRET_KEY = "test-secret"
    try:
        yield
    finally:
        settings.JWT_SECRET_KEY = previous_secret


def _usuario(**overrides) -> Usuario:
    data = {
        "nome": "Ana Contadora",
        "login": "ana.contadora",
        "email": "ana.contadora@example.com",
        "senha_hash": "$argon2id$v=19$hash-de-teste",
        "papel": "contador",
    }
    data.update(overrides)
    return Usuario(**data)


def _credentials_for(user_id: int) -> HTTPAuthorizationCredentials:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "contador",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=12),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _expired_credentials_for(user_id: int) -> HTTPAuthorizationCredentials:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "contador",
            "type": "access",
            "iat": now - timedelta(hours=13),
            "exp": now - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _malformed_credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token-malformado",
    )


def test_get_current_user_returns_active_user_for_valid_access_token(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    current_user = get_current_user(
        credentials=_credentials_for(usuario.id),
        db=session,
    )

    assert current_user.id == usuario.id
    assert current_user.login == "ana.contadora"


def test_get_current_user_rejects_expired_access_token(session):
    usuario = _usuario()
    session.add(usuario)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            credentials=_expired_credentials_for(usuario.id),
            db=session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token expirado"


def test_get_current_user_rejects_malformed_token(session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            credentials=_malformed_credentials(),
            db=session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token inválido"


def test_get_current_user_rejects_inactive_user_even_with_valid_token(session):
    usuario = _usuario(is_active=False)
    session.add(usuario)
    session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            credentials=_credentials_for(usuario.id),
            db=session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Usuário inativo"


def test_get_current_user_rejects_missing_user_even_with_valid_token(session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(
            credentials=_credentials_for(999),
            db=session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token inválido"
