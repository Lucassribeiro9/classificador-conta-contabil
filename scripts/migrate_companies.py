from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from core.models import Empresa


class CompanyMigrationConflict(RuntimeError):
    """Raised when a source company matches conflicting target identity fields."""


@dataclass(frozen=True)
class CompanyMigrationResult:
    created: int = 0
    updated: int = 0


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value

    if isinstance(value, str):
        return datetime.fromisoformat(value)

    raise ValueError(f"Unsupported created_at value: {value!r}")


def _source_company_rows(source_sqlite_url: str) -> list[dict[str, Any]]:
    source_url = make_url(source_sqlite_url)
    if source_url.get_backend_name() != "sqlite":
        raise ValueError("source_sqlite_url must point to a SQLite database")

    engine = create_engine(source_sqlite_url)
    columns = {column["name"] for column in inspect(engine).get_columns("empresas")}
    required_columns = {
        "nome_empresa",
        "cnpj_cpf",
        "api_key",
        "cod_dominio",
        "is_active",
    }
    missing_columns = required_columns - columns
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Source empresas table is missing required columns: {missing}")

    selected_columns = [
        "nome_empresa",
        "cnpj_cpf",
        "api_key",
        "cod_dominio",
        "is_active",
    ]
    if "created_at" in columns:
        selected_columns.append("created_at")

    query = text(f"select {', '.join(selected_columns)} from empresas order by id")
    with engine.connect() as connection:
        rows = [dict(row) for row in connection.execute(query).mappings()]

    for row in rows:
        row["is_active"] = bool(row["is_active"])
        row["created_at"] = _parse_datetime(row.get("created_at"))

    return rows


def _conflicting_field(target: Empresa, source_company: dict[str, Any]) -> str | None:
    for field in ("cnpj_cpf", "cod_dominio", "api_key"):
        if getattr(target, field) != source_company[field]:
            return field

    return None


def _find_target_company(session, source_company: dict[str, Any]) -> Empresa | None:
    candidates = (
        session.execute(
            select(Empresa).where(
                (Empresa.cnpj_cpf == source_company["cnpj_cpf"])
                | (Empresa.cod_dominio == source_company["cod_dominio"])
                | (Empresa.api_key == source_company["api_key"])
            )
        )
        .scalars()
        .all()
    )

    if not candidates:
        return None

    if len(candidates) > 1:
        raise CompanyMigrationConflict(
            "Source company matches multiple target companies by cnpj_cpf, "
            "cod_dominio or api_key"
        )

    conflict = _conflicting_field(candidates[0], source_company)
    if conflict:
        raise CompanyMigrationConflict(
            "Conflicting company identity for cnpj_cpf, cod_dominio or api_key; "
            f"first divergent field is {conflict}: {source_company[conflict]!r}"
        )

    return candidates[0]


def _apply_company_fields(target: Empresa, source_company: dict[str, Any]) -> None:
    target.nome_empresa = source_company["nome_empresa"]
    target.cnpj_cpf = source_company["cnpj_cpf"]
    target.api_key = source_company["api_key"]
    target.cod_dominio = source_company["cod_dominio"]
    target.is_active = source_company["is_active"]
    if source_company.get("created_at") is not None:
        target.created_at = source_company["created_at"]


def _company_needs_update(target: Empresa, source_company: dict[str, Any]) -> bool:
    fields = ("nome_empresa", "cnpj_cpf", "api_key", "cod_dominio", "is_active")
    if any(getattr(target, field) != source_company[field] for field in fields):
        return True

    if source_company.get("created_at") is not None:
        return target.created_at != source_company["created_at"]

    return False


def migrate_companies(source_sqlite_url: str, target_database_url: str) -> CompanyMigrationResult:
    source_companies = _source_company_rows(source_sqlite_url)
    target_engine = create_engine(target_database_url)
    Session = sessionmaker(bind=target_engine)

    created = 0
    updated = 0

    with Session() as session:
        for source_company in source_companies:
            target_company = _find_target_company(session, source_company)
            if target_company is None:
                target_company = Empresa(
                    nome_empresa=source_company["nome_empresa"],
                    cnpj_cpf=source_company["cnpj_cpf"],
                    api_key=source_company["api_key"],
                    cod_dominio=source_company["cod_dominio"],
                    is_active=source_company["is_active"],
                )
                if source_company.get("created_at") is not None:
                    target_company.created_at = source_company["created_at"]
                session.add(target_company)
                created += 1
            else:
                if _company_needs_update(target_company, source_company):
                    _apply_company_fields(target_company, source_company)
                    updated += 1

        session.commit()

    return CompanyMigrationResult(created=created, updated=updated)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate companies from the legacy SQLite database to PostgreSQL."
    )
    parser.add_argument(
        "--source-sqlite-url",
        required=True,
        help="Explicit SQLite source URL, e.g. sqlite:///./data/classificador.db",
    )
    parser.add_argument(
        "--target-database-url",
        required=True,
        help="Explicit target database URL, e.g. postgresql+psycopg://...",
    )
    args = parser.parse_args()

    result = migrate_companies(args.source_sqlite_url, args.target_database_url)
    print(f"Companies migrated: created={result.created}, updated={result.updated}")


if __name__ == "__main__":
    main()
