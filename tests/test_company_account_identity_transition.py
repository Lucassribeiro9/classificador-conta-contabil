from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.database import Base
from core.conta_contabil_empresa import (
    garantir_identidade_contabil,
    resolver_contas_contabeis,
)
from core.models import ContaContabil, ContaContabilEmpresa, Empresa, EmpresaContaContabil


def test_company_account_link_persists_company_identity_reference():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            empresa = Empresa(
                nome_empresa="Empresa sintetica",
                api_key="identity-transition",
                cnpj_cpf="12345678000199",
                cod_dominio=517001,
            )
            session.add(empresa)
            session.flush()
            identidade = ContaContabilEmpresa(
                empresa_id=empresa.id,
                codigo=10046,
                classificacao="1.1.1",
                nome="Banco da empresa",
                tipo="A",
                grau=3,
            )
            session.add(identidade)
            session.flush()

            session.add(
                EmpresaContaContabil(
                    empresa_id=empresa.id,
                    conta_codigo=10046,
                    conta_contabil_empresa_id=identidade.id,
                    quantidade_lancamentos=1,
                    ultima_utilizacao=date(2026, 1, 31),
                )
            )
            session.commit()

            vinculo = session.scalar(select(EmpresaContaContabil))
            assert vinculo.conta_contabil_empresa_id == identidade.id
            assert vinculo.identidade_empresa.nome == "Banco da empresa"
    finally:
        engine.dispose()


def test_company_context_creates_identity_from_legacy_account_once():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            empresa = Empresa(
                nome_empresa="Empresa sintetica",
                api_key="identity-create",
                cnpj_cpf="12345678000270",
                cod_dominio=517002,
            )
            legado = ContaContabil(
                codigo=10046,
                classificacao="1.1.1",
                nome="Banco legado",
                tipo="A",
                grau=3,
                is_financial_origin=True,
            )
            session.add_all([empresa, legado])
            session.flush()

            primeira = garantir_identidade_contabil(
                session, empresa_id=empresa.id, codigo=legado.codigo
            )
            segunda = garantir_identidade_contabil(
                session, empresa_id=empresa.id, codigo=legado.codigo
            )

            assert primeira is segunda
            assert primeira.nome == "Banco legado"
            assert primeira.is_financial_origin is True
            assert len(session.scalars(select(ContaContabilEmpresa)).all()) == 1
    finally:
        engine.dispose()


def test_batch_resolution_never_returns_identity_from_another_company():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            primeira = Empresa(
                nome_empresa="Empresa A",
                api_key="batch-a",
                cnpj_cpf="12345678000350",
                cod_dominio=517003,
            )
            segunda = Empresa(
                nome_empresa="Empresa B",
                api_key="batch-b",
                cnpj_cpf="12345678000430",
                cod_dominio=517004,
            )
            session.add_all([primeira, segunda])
            session.flush()
            session.add_all(
                [
                    ContaContabilEmpresa(
                        empresa_id=primeira.id,
                        codigo=10046,
                        classificacao="1.1",
                        nome="Banco A",
                        tipo="A",
                        grau=2,
                    ),
                    ContaContabilEmpresa(
                        empresa_id=segunda.id,
                        codigo=10046,
                        classificacao="2.1",
                        nome="Despesa B",
                        tipo="A",
                        grau=2,
                    ),
                ]
            )
            session.flush()

            resultado = resolver_contas_contabeis(
                session, empresa_id=primeira.id, codigos={10046}
            )

            assert resultado[10046].nome == "Banco A"
            assert resultado[10046].empresa_id == primeira.id
    finally:
        engine.dispose()
