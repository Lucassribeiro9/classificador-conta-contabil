"""Migration real da referência entre vínculo legado e identidade empresarial."""

from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, text

from tests.integration.test_postgresql_integration import _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_migration_backfills_matching_company_identity_and_is_reversible():
    engine = create_engine(_postgres_database_url())
    config = Config("alembic.ini")
    suffix = uuid4().hex[:10]
    codigo = 600_000_000 + int(suffix, 16) % 100_000_000
    empresa_id: int | None = None
    conta_id: int | None = None
    identidade_id: int | None = None
    vinculo_id: int | None = None

    command.downgrade(config, "516b4c8d2e10")
    try:
        with engine.begin() as connection:
            empresa_id = connection.execute(
                text(
                    """
                    INSERT INTO empresas
                        (nome_empresa, api_key, cnpj_cpf, cod_dominio,
                         is_active, created_at)
                    VALUES (:nome, :api_key, :cnpj, :dominio, true, now())
                    RETURNING id
                    """
                ),
                {
                    "nome": f"Empresa migration {suffix}",
                    "api_key": f"migration-{suffix}",
                    "cnpj": f"{int(suffix, 16) % 10**14:014d}",
                    "dominio": int(suffix, 16) % 2_000_000_000,
                },
            ).scalar_one()
            conta_id = connection.execute(
                text(
                    """
                    INSERT INTO contas_contabeis
                        (codigo, classificacao, nome, tipo, grau,
                         is_active, is_financial_origin, created_at, updated_at)
                    VALUES (:codigo, '1.1', 'Conta migration', 'A', 2,
                            true, false, now(), now())
                    RETURNING id
                    """
                ),
                {"codigo": codigo},
            ).scalar_one()
            identidade_id = connection.execute(
                text(
                    """
                    INSERT INTO contas_contabeis_empresas
                        (empresa_id, codigo, classificacao, nome, tipo, grau)
                    VALUES (:empresa_id, :codigo, '1.1', 'Conta migration', 'A', 2)
                    RETURNING id
                    """
                ),
                {"empresa_id": empresa_id, "codigo": codigo},
            ).scalar_one()
            vinculo_id = connection.execute(
                text(
                    """
                    INSERT INTO empresa_contas_contabeis
                        (empresa_id, conta_codigo, quantidade_lancamentos,
                         ultima_utilizacao, created_at, updated_at)
                    VALUES (:empresa_id, :codigo, 1, CURRENT_DATE, now(), now())
                    RETURNING id
                    """
                ),
                {"empresa_id": empresa_id, "codigo": codigo},
            ).scalar_one()

        command.upgrade(config, "head")

        with engine.connect() as connection:
            reference = connection.execute(
                text(
                    """
                    SELECT conta_contabil_empresa_id
                    FROM empresa_contas_contabeis
                    WHERE id = :vinculo_id
                    """
                ),
                {"vinculo_id": vinculo_id},
            ).scalar_one()
        assert reference == identidade_id
    finally:
        command.upgrade(config, "head")
        if empresa_id is not None:
            with engine.begin() as connection:
                if vinculo_id is not None:
                    connection.execute(
                        text("DELETE FROM empresa_contas_contabeis WHERE id = :id"),
                        {"id": vinculo_id},
                    )
                if identidade_id is not None:
                    connection.execute(
                        text("DELETE FROM contas_contabeis_empresas WHERE id = :id"),
                        {"id": identidade_id},
                    )
                if conta_id is not None:
                    connection.execute(
                        text("DELETE FROM contas_contabeis WHERE id = :id"),
                        {"id": conta_id},
                    )
                connection.execute(
                    text("DELETE FROM empresas WHERE id = :id"),
                    {"id": empresa_id},
                )
        engine.dispose()
