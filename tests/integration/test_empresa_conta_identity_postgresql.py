"""Constraints reais da identidade contabil por empresa em PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.conta_contabil_empresa import garantir_identidade_contabil
from core.models import ContaContabil, ContaContabilEmpresa, Empresa
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


def test_vinculo_legado_nao_aceita_identidade_de_outra_empresa():
    engine = create_engine(_postgres_database_url())
    suffix = uuid4().hex[:10]
    codigo = 800_000_000 + int(suffix, 16) % 100_000_000
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                empresas = []
                for numero in (1, 2):
                    empresas.append(
                        connection.execute(
                            text(
                                """
                                INSERT INTO empresas
                                    (nome_empresa, api_key, cnpj_cpf, cod_dominio,
                                     is_active, created_at)
                                VALUES (:nome, :api_key, :cnpj, :codigo, true, now())
                                RETURNING id
                                """
                            ),
                            {
                                "nome": f"Empresa vínculo {suffix}-{numero}",
                                "api_key": f"vinculo-{suffix}-{numero}",
                                "cnpj": f"{(int(suffix, 16) + numero) % 10**14:014d}",
                                "codigo": (int(suffix, 16) + numero) % 2_000_000_000,
                            },
                        ).scalar_one()
                    )
                connection.execute(
                    text(
                        """
                        INSERT INTO contas_contabeis
                            (codigo, classificacao, nome, tipo, grau,
                             is_active, is_financial_origin, created_at, updated_at)
                        VALUES (:codigo, '1.1', 'Conta vínculo', 'A', 2,
                                true, false, now(), now())
                        """
                    ),
                    {"codigo": codigo},
                )
                identidade_outra_empresa = connection.execute(
                    text(
                        """
                        INSERT INTO contas_contabeis_empresas
                            (empresa_id, codigo, classificacao, nome, tipo, grau)
                        VALUES (:empresa_id, :codigo, '1.1', 'Conta outra empresa', 'A', 2)
                        RETURNING id
                        """
                    ),
                    {"empresa_id": empresas[1], "codigo": codigo},
                ).scalar_one()

                with pytest.raises(IntegrityError):
                    with connection.begin_nested():
                        connection.execute(
                            text(
                                """
                                INSERT INTO empresa_contas_contabeis
                                    (empresa_id, conta_codigo,
                                     conta_contabil_empresa_id,
                                     quantidade_lancamentos, ultima_utilizacao,
                                     created_at, updated_at)
                                VALUES (:empresa_id, :codigo, :identidade_id,
                                        1, CURRENT_DATE, now(), now())
                                """
                            ),
                            {
                                "empresa_id": empresas[0],
                                "codigo": codigo,
                                "identidade_id": identidade_outra_empresa,
                            },
                        )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_criacao_concorrente_reutiliza_a_mesma_identidade_da_empresa():
    engine = create_engine(_postgres_database_url())
    suffix = uuid4().hex[:10]
    codigo = 900_000_000 + int(suffix, 16) % 90_000_000
    with Session(engine) as session:
        empresa = Empresa(
            nome_empresa=f"Empresa concorrência {suffix}",
            api_key=f"concorrencia-{suffix}",
            cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
            cod_dominio=int(suffix, 16) % 2_000_000_000,
        )
        conta = ContaContabil(
            codigo=codigo,
            classificacao="1.1",
            nome="Conta concorrente",
            tipo="A",
            grau=2,
        )
        session.add_all([empresa, conta])
        session.commit()
        empresa_id, conta_id = empresa.id, conta.id

    barrier = Barrier(2)

    def create_identity() -> int:
        with Session(engine) as session:
            barrier.wait()
            identidade = garantir_identidade_contabil(
                session,
                empresa_id=empresa_id,
                codigo=codigo,
            )
            assert identidade is not None
            session.commit()
            return identidade.id

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = [
                future.result()
                for future in (
                    executor.submit(create_identity),
                    executor.submit(create_identity),
                )
            ]

        assert ids[0] == ids[1]
        with Session(engine) as session:
            assert (
                session.query(ContaContabilEmpresa)
                .filter_by(empresa_id=empresa_id, codigo=codigo)
                .count()
                == 1
            )
    finally:
        with Session(engine) as session:
            session.query(ContaContabilEmpresa).filter_by(
                empresa_id=empresa_id,
                codigo=codigo,
            ).delete()
            session.query(ContaContabil).filter_by(id=conta_id).delete()
            session.query(Empresa).filter_by(id=empresa_id).delete()
            session.commit()
        engine.dispose()
