import subprocess
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import Usuario
from scripts.bootstrap_admin import bootstrap_admin


@pytest.fixture()
def database_url():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield "sqlite://", engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _session(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_bootstrap_admin_creates_admin_without_plaintext_password(database_url):
    _, engine = database_url

    result = bootstrap_admin(
        database_url="sqlite://",
        nome="Admin Interno",
        login="admin",
        email="admin@example.com",
        password="senha-segura-123",
        engine=engine,
    )

    with _session(engine) as session:
        admin = session.query(Usuario).one()

    assert result.created is True
    assert admin.nome == "Admin Interno"
    assert admin.login == "admin"
    assert admin.email == "admin@example.com"
    assert admin.papel == "admin"
    assert admin.is_active is True
    assert admin.senha_hash != "senha-segura-123"
    assert admin.senha_hash.startswith("$argon2")


@pytest.mark.parametrize(
    ("existing_field", "existing_value"),
    [
        ("login", "admin"),
        ("email", "admin@example.com"),
    ],
)
def test_bootstrap_admin_is_idempotent_for_existing_login_or_email(
    database_url,
    existing_field,
    existing_value,
):
    _, engine = database_url

    bootstrap_admin(
        database_url="sqlite://",
        nome="Admin Inicial",
        login="admin",
        email="admin@example.com",
        password="senha-segura-123",
        engine=engine,
    )
    result = bootstrap_admin(
        database_url="sqlite://",
        nome="Admin Reexecutado",
        login=existing_value if existing_field == "login" else "outro-login",
        email=existing_value if existing_field == "email" else "outro@example.com",
        password="outra-senha",
        engine=engine,
    )

    with _session(engine) as session:
        admins = session.query(Usuario).all()

    assert result.created is False
    assert len(admins) == 1
    assert admins[0].nome == "Admin Inicial"


def test_bootstrap_admin_cli_fails_clearly_when_required_arguments_are_missing():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.bootstrap_admin", "--nome", "Admin"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--login" in result.stderr
    assert "--email" in result.stderr


def test_bootstrap_admin_cli_does_not_accept_password_argument():
    result = subprocess.run(
        [sys.executable, "-m", "scripts.bootstrap_admin", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--password" not in result.stdout
    assert "--nome" in result.stdout
    assert "--login" in result.stdout
    assert "--email" in result.stdout
