import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
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


def test_razao_job_identity_is_unique_under_concurrent_inserts():
    database_url = _postgres_database_url()
    engine = create_engine(database_url)
    suffix = uuid4().hex[:10]
    with engine.begin() as connection:
        empresa_id = connection.execute(
            text(
                """
                INSERT INTO empresas
                    (nome_empresa, api_key, cnpj_cpf, cod_dominio, is_active, created_at)
                VALUES (:nome, :api_key, :cnpj, :codigo, true, now())
                RETURNING id
                """
            ),
            {
                "nome": f"Empresa concorrencia {suffix}",
                "api_key": f"api-{suffix}",
                "cnpj": f"{int(suffix, 16) % 10**14:014d}",
                "codigo": int(suffix, 16) % 2_000_000_000,
            },
        ).scalar_one()
        usuario_id = connection.execute(
            text(
                """
                INSERT INTO usuarios
                    (nome, login, email, senha_hash, papel, is_active, created_at, updated_at)
                VALUES (:nome, :login, :email, :senha, 'operador', true, now(), now())
                RETURNING id
                """
            ),
            {
                "nome": "Operador concorrencia",
                "login": f"operador-{suffix}",
                "email": f"operador-{suffix}@example.com",
                "senha": "hash-de-teste",
            },
        ).scalar_one()

    barrier = Barrier(2)

    def insert_same_job() -> str:
        with engine.connect() as connection:
            transaction = connection.begin()
            barrier.wait()
            try:
                connection.execute(
                    text(
                        """
                        INSERT INTO lotes_importacao_razao
                            (empresa_id, usuario_id, original_filename, file_hash,
                             status, total_linhas, linhas_processadas,
                             total_importadas, total_invalidas, warnings_total,
                             attempt_count, created_at, updated_at)
                        VALUES
                            (:empresa_id, :usuario_id, 'razao.xlsx', :file_hash,
                             'queued', NULL, 0, 0, 0, 0, 0, now(), now())
                        """
                    ),
                    {
                        "empresa_id": empresa_id,
                        "usuario_id": usuario_id,
                        "file_hash": f"sha256:{suffix}",
                    },
                )
                transaction.commit()
                return "created"
            except IntegrityError:
                transaction.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: insert_same_job(), range(2)))

    engine.dispose()
    assert sorted(results) == ["conflict", "created"]
