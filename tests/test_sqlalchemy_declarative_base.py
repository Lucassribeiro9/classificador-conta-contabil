from pathlib import Path

from sqlalchemy.orm import DeclarativeBase

from core.database import Base
from core import models


ROOT = Path(__file__).resolve().parents[1]


def test_orm_base_uses_sqlalchemy_2_declarative_base():
    assert issubclass(Base, DeclarativeBase)


def test_current_models_remain_registered_in_base_metadata():
    assert models.Empresa.__table__ is Base.metadata.tables["empresas"]
    assert models.Transacao.__table__ is Base.metadata.tables["transacoes"]


def test_spec_records_declarative_base_decision_as_approved():
    spec = (ROOT / "docs/specs/01-postgresql-migracao.md").read_text(
        encoding="utf-8"
    )

    assert "DeclarativeBase" in spec
    assert (
        "A base ORM usa `sqlalchemy.orm.DeclarativeBase`"
        in spec
    )
    assert (
        "A migracao para `sqlalchemy.orm.DeclarativeBase` sera feita junto"
        not in spec
    )
