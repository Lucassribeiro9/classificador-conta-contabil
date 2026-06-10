import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from api.dependencies import get_db
from api.main import app


pytestmark = pytest.mark.integration_postgres

ROOT = Path(__file__).resolve().parents[2]


def _postgres_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL deve estar definido para testes PostgreSQL.")

    if make_url(database_url).get_backend_name() != "postgresql":
        pytest.fail("DATABASE_URL deve apontar para PostgreSQL nos testes de integracao.")

    return database_url


def test_alembic_migrations_apply_to_postgresql_head():
    database_url = _postgres_database_url()
    alembic_config = Config(str(ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(alembic_config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_heads = set(context.get_current_heads())

        expected_heads = set(ScriptDirectory.from_config(alembic_config).get_heads())
        assert current_heads == expected_heads
    finally:
        engine.dispose()


def test_health_endpoint_uses_real_postgresql_database():
    database_url = _postgres_database_url()
    engine = create_engine(database_url)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/health")
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["database"] == "online"
