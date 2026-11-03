"""PostgreSQL contract for immutable, company-scoped dataset manifests."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.dataset_builder import build_dataset_treino_contrapartida, reconstruct_dataset_from_manifest
from core.models import Empresa
from tests.integration.test_postgresql_integration import ROOT, _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_manifest_migration_persists_and_rejects_mutation_across_companies():
    url = _postgres_database_url()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    suffix = int(uuid4().hex[:10], 16)
    try:
        with Session(engine) as session:
            companies = [
                Empresa(
                    nome_empresa=f"Dataset manifesto teste {suffix}-{index}",
                    api_key=f"dataset-manifesto-{suffix}-{index}",
                    cnpj_cpf=f"{(suffix + index) % 10**14:014d}",
                    cod_dominio=(suffix + index) % 2_000_000_000,
                )
                for index in range(2)
            ]
            session.add_all(companies)
            session.flush()
            first = build_dataset_treino_contrapartida(session, empresa_id=companies[0].id)
            session.commit()

            assert reconstruct_dataset_from_manifest(
                session, empresa_id=companies[0].id, manifest_id=first.manifesto["id"]
            ) == []
            with pytest.raises(ValueError, match="Manifesto não encontrado"):
                reconstruct_dataset_from_manifest(
                    session, empresa_id=companies[1].id, manifest_id=first.manifesto["id"]
                )
            with pytest.raises(DBAPIError):
                with session.begin_nested():
                    session.execute(text(
                        "UPDATE dataset_manifests SET content_hash = :hash WHERE id = :id"
                    ), {"hash": "0" * 64, "id": first.manifesto["id"]})
            session.rollback()
    finally:
        engine.dispose()
