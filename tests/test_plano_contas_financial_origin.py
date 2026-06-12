import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import ContaContabil
from core.plano_contas_financeiro import infer_is_financial_origin
from core.plano_contas_importer import import_plano_contas


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


@pytest.mark.parametrize(
    ("nome", "classificacao"),
    [
        ("CAIXA", "1.1.01.01"),
        ("BANCOS CONTA CORRENTE", "1.1.01.02"),
        ("BCO. SANTANDER ( BRASIL ) S.A.", "1.1.01.01.02.10046"),
        ("APLICACOES FINANCEIRAS", "1.1.02.03"),
    ],
)
def test_infer_is_financial_origin_marks_financial_accounts(nome, classificacao):
    assert infer_is_financial_origin(nome=nome, classificacao=classificacao) is True


@pytest.mark.parametrize(
    ("nome", "classificacao"),
    [
        ("IRRF A RECOLHER", "2.1.04.01"),
        ("DUPLICATAS A RECEBER", "1.1.03.01"),
    ],
)
def test_infer_is_financial_origin_does_not_mark_common_non_financial_accounts(
    nome,
    classificacao,
):
    assert infer_is_financial_origin(nome=nome, classificacao=classificacao) is False


def test_import_plano_contas_persists_inferred_financial_origin_flag(session):
    import_plano_contas(
        session,
        [
            {
                "codigo": 10046,
                "classificacao": "1.1.01.01.02.10046",
                "nome": "BCO. SANTANDER ( BRASIL ) S.A.",
                "tipo": "A",
                "grau": 6,
            },
            {
                "codigo": 50057,
                "classificacao": "2.1.04.01",
                "nome": "IRRF A RECOLHER",
                "tipo": "A",
                "grau": 5,
            },
        ],
    )

    contas = {
        conta.codigo: conta
        for conta in session.query(ContaContabil).order_by(ContaContabil.codigo).all()
    }
    assert contas[10046].is_financial_origin is True
    assert contas[50057].is_financial_origin is False
