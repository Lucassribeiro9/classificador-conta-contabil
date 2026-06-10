from datetime import datetime
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.models import Empresa, Transacao
from scripts.migrate_companies import CompanyMigrationConflict, migrate_companies


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _create_source_database(path: Path) -> str:
    engine = create_engine(_sqlite_url(path))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                create table empresas (
                    id integer primary key,
                    nome_empresa varchar(100) not null,
                    api_key varchar(70) not null,
                    cnpj_cpf varchar(14) not null,
                    cod_dominio integer not null,
                    is_active boolean not null,
                    created_at datetime
                )
                """
            )
        )
        connection.execute(
            text(
                """
                create table transacoes (
                    id integer primary key,
                    empresa_id integer not null,
                    data date not null,
                    historico varchar not null,
                    valor numeric not null
                )
                """
            )
        )

    return _sqlite_url(path)


def _create_target_database(path: Path) -> str:
    engine = create_engine(_sqlite_url(path))
    Base.metadata.create_all(bind=engine)
    return _sqlite_url(path)


def _insert_source_company(
    source_url: str,
    *,
    nome_empresa: str = "Empresa Origem LTDA",
    cnpj_cpf: str = "12345678000199",
    api_key: str = "api-key-origem",
    cod_dominio: int = 1001,
    is_active: bool = True,
    created_at: str = "2026-01-02 03:04:05",
) -> None:
    engine = create_engine(source_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                insert into empresas (
                    nome_empresa, cnpj_cpf, api_key, cod_dominio, is_active, created_at
                )
                values (
                    :nome_empresa, :cnpj_cpf, :api_key, :cod_dominio, :is_active, :created_at
                )
                """
            ),
            {
                "nome_empresa": nome_empresa,
                "cnpj_cpf": cnpj_cpf,
                "api_key": api_key,
                "cod_dominio": cod_dominio,
                "is_active": is_active,
                "created_at": created_at,
            },
        )


def _insert_source_transaction(source_url: str) -> None:
    engine = create_engine(source_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                insert into transacoes (empresa_id, data, historico, valor)
                values (1, '2026-01-10', 'fora do escopo', 10.00)
                """
            )
        )


def _target_session(target_url: str):
    engine = create_engine(target_url)
    return sessionmaker(bind=engine)()


def test_migrate_companies_creates_or_updates_companies_without_transactions(tmp_path):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")
    _insert_source_company(source_url)
    _insert_source_transaction(source_url)

    result = migrate_companies(source_url, target_url)

    with _target_session(target_url) as session:
        companies = session.query(Empresa).all()
        transactions = session.query(Transacao).all()

    assert result.created == 1
    assert result.updated == 0
    assert len(companies) == 1
    assert companies[0].nome_empresa == "Empresa Origem LTDA"
    assert companies[0].cnpj_cpf == "12345678000199"
    assert companies[0].api_key == "api-key-origem"
    assert companies[0].cod_dominio == 1001
    assert companies[0].is_active is True
    assert companies[0].created_at == datetime(2026, 1, 2, 3, 4, 5)
    assert transactions == []


def test_migrate_companies_is_idempotent_and_updates_existing_company(tmp_path):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")
    _insert_source_company(source_url, nome_empresa="Nome Inicial")
    migrate_companies(source_url, target_url)

    engine = create_engine(source_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                update empresas
                set nome_empresa = 'Nome Atualizado', is_active = 0
                where cnpj_cpf = '12345678000199'
                """
            )
        )

    result = migrate_companies(source_url, target_url)

    with _target_session(target_url) as session:
        companies = session.query(Empresa).all()

    assert result.created == 0
    assert result.updated == 1
    assert len(companies) == 1
    assert companies[0].nome_empresa == "Nome Atualizado"
    assert companies[0].is_active is False


def test_migrate_companies_second_run_without_changes_does_not_duplicate_or_update(
    tmp_path,
):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")
    _insert_source_company(source_url)

    first_result = migrate_companies(source_url, target_url)
    second_result = migrate_companies(source_url, target_url)

    with _target_session(target_url) as session:
        companies = session.query(Empresa).all()

    assert first_result.created == 1
    assert first_result.updated == 0
    assert second_result.created == 0
    assert second_result.updated == 0
    assert len(companies) == 1


def test_migrate_companies_cli_requires_explicit_source_and_target_urls(tmp_path):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")
    _insert_source_company(source_url)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.migrate_companies",
            "--source-sqlite-url",
            source_url,
            "--target-database-url",
            target_url,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with _target_session(target_url) as session:
        companies = session.query(Empresa).all()

    assert "created=1, updated=0" in result.stdout
    assert len(companies) == 1


def test_migrate_companies_rejects_source_matching_multiple_target_companies(tmp_path):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")

    _insert_source_company(
        source_url,
        cnpj_cpf="12345678000199",
        api_key="api-key-origem",
        cod_dominio=1001,
    )

    with _target_session(target_url) as session:
        session.add(
            Empresa(
                nome_empresa="Empresa com CNPJ",
                cnpj_cpf="12345678000199",
                api_key="api-key-cnpj",
                cod_dominio=2001,
            )
        )
        session.add(
            Empresa(
                nome_empresa="Empresa com API key",
                cnpj_cpf="99999999000199",
                api_key="api-key-origem",
                cod_dominio=2002,
            )
        )
        session.commit()

    with pytest.raises(CompanyMigrationConflict, match="multiple target companies"):
        migrate_companies(source_url, target_url)


@pytest.mark.parametrize(
    ("field", "target_value", "source_value"),
    [
        ("cnpj_cpf", "12345678000199", "12345678000199"),
        ("cod_dominio", 1001, 1001),
        ("api_key", "api-key-origem", "api-key-origem"),
    ],
)
def test_migrate_companies_rejects_conflicting_existing_company(
    tmp_path, field, target_value, source_value
):
    source_url = _create_source_database(tmp_path / "source.db")
    target_url = _create_target_database(tmp_path / "target.db")

    source_company = {
        "nome_empresa": "Empresa Origem",
        "cnpj_cpf": "12345678000199",
        "api_key": "api-key-origem",
        "cod_dominio": 1001,
    }
    target_company = {
        "nome_empresa": "Empresa Destino",
        "cnpj_cpf": "99999999000199",
        "api_key": "api-key-destino",
        "cod_dominio": 9999,
    }
    source_company[field] = source_value
    target_company[field] = target_value

    _insert_source_company(source_url, **source_company)

    with _target_session(target_url) as session:
        session.add(Empresa(**target_company))
        session.commit()

    with pytest.raises(CompanyMigrationConflict, match=field):
        migrate_companies(source_url, target_url)
