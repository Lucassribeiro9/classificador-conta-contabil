import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import ContaContabil, LancamentoRazaoNormalizado
from core.razao_catalog_validator import validate_lancamento_razao_contas


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


def _conta(codigo):
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
    )


def test_validate_razao_accounts_accepts_entry_when_origin_and_counterpart_exist(
    session,
):
    session.add_all([_conta(10046), _conta(20001)])
    session.flush()

    result = validate_lancamento_razao_contas(
        session,
        {"conta_origem": "10046", "conta_contrapartida": "20001"},
    )

    assert result.is_valid is True
    assert result.warnings == []


def test_validate_razao_accounts_warns_when_origin_is_missing_without_creating_it(
    session,
):
    session.add(_conta(20001))
    session.flush()

    result = validate_lancamento_razao_contas(
        session,
        {"conta_origem": "10046", "conta_contrapartida": "20001"},
    )

    assert result.is_valid is False
    assert result.warnings == [
        "Conta de origem 10046 nao encontrada no catalogo."
    ]
    assert session.query(ContaContabil).count() == 1
    assert session.query(ContaContabil).filter_by(codigo=10046).count() == 0
    assert session.query(LancamentoRazaoNormalizado).count() == 0


def test_validate_razao_accounts_warns_when_counterpart_is_missing_without_creating_it(
    session,
):
    session.add(_conta(10046))
    session.flush()

    result = validate_lancamento_razao_contas(
        session,
        {"conta_origem": "10046", "conta_contrapartida": "20001"},
    )

    assert result.is_valid is False
    assert result.warnings == [
        "Conta de contrapartida 20001 nao encontrada no catalogo."
    ]
    assert session.query(ContaContabil).count() == 1
    assert session.query(ContaContabil).filter_by(codigo=20001).count() == 0
    assert session.query(LancamentoRazaoNormalizado).count() == 0
