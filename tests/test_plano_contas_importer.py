import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import ContaContabil
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


def _conta(**overrides):
    data = {
        "codigo": 10046,
        "classificacao": "1.1.01.01.02.10046",
        "nome": "BCO. SANTANDER",
        "tipo": "A",
        "grau": 6,
        "is_financial_origin": True,
    }
    data.update(overrides)
    return data


def test_import_plano_contas_creates_new_accounts_and_returns_summary(session):
    result = import_plano_contas(
        session,
        [
            _conta(codigo=1000, classificacao="1", nome="ATIVO", tipo="S", grau=1),
            _conta(),
        ],
    )

    assert result.criadas == 2
    assert result.atualizadas == 0
    assert result.ignoradas == 0
    assert result.invalidas == 0

    contas = session.query(ContaContabil).order_by(ContaContabil.codigo).all()
    assert [conta.codigo for conta in contas] == [1000, 10046]
    assert contas[0].tipo == "S"
    assert contas[0].is_active is True
    assert contas[1].is_financial_origin is True


def test_import_plano_contas_reimport_is_idempotent_without_duplicates(session):
    contas = [_conta()]
    import_plano_contas(session, contas)

    result = import_plano_contas(session, contas)

    assert result.criadas == 0
    assert result.atualizadas == 0
    assert result.ignoradas == 1
    assert result.invalidas == 0
    assert session.query(ContaContabil).count() == 1


def test_import_plano_contas_updates_existing_account_when_fields_change(session):
    import_plano_contas(session, [_conta(nome="BCO. SANTANDER", tipo="A")])

    result = import_plano_contas(
        session,
        [
            _conta(
                nome="BANCO SANTANDER BRASIL",
                classificacao="1.1.01.01.02.10046",
                tipo="S",
                grau=5,
                is_financial_origin=False,
            )
        ],
    )

    assert result.criadas == 0
    assert result.atualizadas == 1
    assert result.ignoradas == 0
    assert result.invalidas == 0

    saved = session.query(ContaContabil).one()
    assert saved.nome == "BANCO SANTANDER BRASIL"
    assert saved.tipo == "S"
    assert saved.grau == 5
    assert saved.is_financial_origin is False


def test_import_plano_contas_keeps_missing_accounts_active(session):
    import_plano_contas(session, [_conta(codigo=1000), _conta(codigo=10046)])

    import_plano_contas(session, [_conta(codigo=10046, nome="BANCO SANTANDER")])

    missing_from_second_import = (
        session.query(ContaContabil).filter(ContaContabil.codigo == 1000).one()
    )
    assert missing_from_second_import.is_active is True
    assert session.query(ContaContabil).count() == 2


def test_import_plano_contas_reports_invalid_rows_without_persisting_them(session):
    result = import_plano_contas(
        session,
        [
            _conta(codigo=10046),
            {"codigo": None, "tipo": "A", "classificacao": "1", "nome": "INVALIDA"},
        ],
    )

    assert result.criadas == 1
    assert result.atualizadas == 0
    assert result.ignoradas == 0
    assert result.invalidas == 1
    assert session.query(ContaContabil).count() == 1
