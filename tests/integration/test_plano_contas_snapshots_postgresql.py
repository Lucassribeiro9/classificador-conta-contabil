"""Integridade temporal e concorrência em PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core.models import Empresa, PlanoContasImportEvent, ReviewItem
from core.plano_contas_snapshots import (
    SnapshotConflict,
    importar_snapshot,
    selecionar_snapshot,
)
from tests.integration.test_postgresql_integration import ROOT, _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_concurrent_imports_create_review_and_history_is_immutable():
    url = _postgres_database_url()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    suffix = uuid4().hex[:10]
    try:
        with Session(engine) as session:
            empresa = Empresa(
                nome_empresa=f"Snapshot {suffix}",
                api_key=f"snapshot-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(empresa)
            session.commit()
            company_id = empresa.id

        barrier = Barrier(2)

        def import_one(nome):
            with Session(engine) as session:
                barrier.wait(timeout=5)
                result = importar_snapshot(
                    session,
                    empresa_id=company_id,
                    contas=[
                        {
                            "codigo": 100,
                            "classificacao": "1.1",
                            "nome": nome,
                            "tipo": "A",
                            "grau": 2,
                        }
                    ],
                    vigencia=date(2026, 2, 1),
                    origem=nome,
                )
                session.commit()
                return result.snapshot.id

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(import_one, ("Banco", "Despesa")))

        assert len(set(ids)) == 2
        with Session(engine) as session:
            events = session.scalars(
                select(PlanoContasImportEvent).where(
                    PlanoContasImportEvent.empresa_id == company_id,
                )
            ).all()
            assert len(events) == 2
            reviews = session.scalars(
                select(ReviewItem).where(
                    ReviewItem.empresa_id == company_id,
                    ReviewItem.source_type == "snapshot_conflict",
                )
            ).all()
            assert len(reviews) == 1
            with pytest.raises(SnapshotConflict):
                selecionar_snapshot(
                    session, empresa_id=company_id, competencia=date(2026, 3, 1)
                )

        with engine.begin() as connection:
            with pytest.raises(DBAPIError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            "UPDATE plano_contas_snapshots SET content_hash = :hash WHERE id = :id"
                        ),
                        {"hash": "0" * 64, "id": ids[0]},
                    )
        with pytest.raises(RuntimeError, match="Snapshot history exists"):
            command.downgrade(config, "-1")
    finally:
        engine.dispose()
