"""Constraints reais da identidade contabil por empresa em PostgreSQL."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.test_postgresql_integration import _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_mesmo_codigo_em_empresas_distintas_e_unico_em_cada_empresa():
    engine = create_engine(_postgres_database_url())
    suffix = uuid4().hex[:10]
    try:
        with engine.begin() as connection:
            empresas = []
            for numero in (1, 2):
                empresa_id = connection.execute(
                    text(
                        """
                        INSERT INTO empresas
                            (nome_empresa, api_key, cnpj_cpf, cod_dominio, is_active,
                             created_at)
                        VALUES (:nome, :api_key, :cnpj, :codigo, true, now())
                        RETURNING id
                        """
                    ),
                    {
                        "nome": f"Empresa identidade {suffix}-{numero}",
                        "api_key": f"identidade-{suffix}-{numero}",
                        "cnpj": f"{(int(suffix, 16) + numero) % 10**14:014d}",
                        "codigo": (int(suffix, 16) + numero) % 2_000_000_000,
                    },
                ).scalar_one()
                empresas.append(empresa_id)

            identidades = []
            for empresa_id, nome in zip(empresas, ("Banco A", "Despesa B")):
                identidade_id = connection.execute(
                    text(
                        """
                        INSERT INTO contas_contabeis_empresas
                            (empresa_id, codigo, classificacao, nome, tipo, grau)
                        VALUES (:empresa_id, 10046, '1.1', :nome, 'A', 2)
                        RETURNING id
                        """
                    ),
                    {"empresa_id": empresa_id, "nome": nome},
                ).scalar_one()
                identidades.append(identidade_id)

            assert identidades[0] != identidades[1]
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(
                        text(
                            """
                            INSERT INTO contas_contabeis_empresas
                                (empresa_id, codigo, classificacao, nome, tipo, grau)
                            VALUES (:empresa_id, 10046, '1.1', 'Duplicada', 'A', 2)
                            """
                        ),
                        {"empresa_id": empresas[0]},
                    )

            nomes = connection.execute(
                text(
                    """
                    SELECT nome FROM contas_contabeis_empresas
                    WHERE empresa_id = :empresa_id AND codigo = 10046
                    """
                ),
                {"empresa_id": empresas[0]},
            ).scalars().all()
            assert nomes == ["Banco A"]
    finally:
        engine.dispose()
