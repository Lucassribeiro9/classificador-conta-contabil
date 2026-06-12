from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import ContaContabil


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


def _conta_contabil(**overrides) -> ContaContabil:
    data = {
        "codigo": 10046,
        "classificacao": "1.1.01.01.02.10046",
        "nome": "BCO. SANTANDER ( BRASIL ) S.A.",
        "tipo": "A",
        "grau": 6,
        "is_financial_origin": True,
    }
    data.update(overrides)
    return ContaContabil(**data)


def test_conta_contabil_can_be_persisted_with_catalog_fields(session):
    conta = _conta_contabil()

    session.add(conta)
    session.commit()

    saved = session.query(ContaContabil).one()
    assert saved.codigo == 10046
    assert saved.classificacao == "1.1.01.01.02.10046"
    assert saved.nome == "BCO. SANTANDER ( BRASIL ) S.A."
    assert saved.tipo == "A"
    assert saved.grau == 6
    assert saved.is_active is True
    assert saved.is_financial_origin is True
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


def test_conta_contabil_codigo_is_unique(session):
    first = _conta_contabil(nome="BANCO 1")
    second = _conta_contabil(nome="BANCO 2")

    session.add_all([first, second])

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("tipo", ["A", "S"])
def test_conta_contabil_accepts_analytic_and_synthetic_types(session, tipo):
    session.add(_conta_contabil(tipo=tipo))

    session.commit()

    assert session.query(ContaContabil).one().tipo == tipo


def test_conta_contabil_rejects_unknown_type(session):
    session.add(_conta_contabil(tipo="X"))

    with pytest.raises(IntegrityError):
        session.commit()
