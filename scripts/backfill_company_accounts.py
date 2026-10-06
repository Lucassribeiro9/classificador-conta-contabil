"""Backfill legacy company-account links into company-scoped identities."""

from dataclasses import dataclass
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from uuid import uuid4

from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from core.database import build_engine_kwargs
from core.models import (
    ContaContabil,
    ContaContabilEmpresa,
    BackfillContasContabeisExecucao,
    BackfillContasContabeisItem,
    EmpresaContaContabil,
)


@dataclass(frozen=True)
class BackfillResult:
    eligible: int = 0
    already_present: int = 0
    conflicts: int = 0
    ineligible: int = 0
    created: int = 0
    failed: int = 0
    run_id: str | None = None
    rolled_back: int = 0
    rollback_blocked: int = 0


_COPIED_FIELDS = (
    "classificacao",
    "nome",
    "tipo",
    "grau",
    "is_active",
    "is_financial_origin",
)


def _fields_match(target: ContaContabilEmpresa, source: ContaContabil) -> bool:
    return all(getattr(target, field) == getattr(source, field) for field in _COPIED_FIELDS)


def _fingerprint(values: dict[str, object]) -> str:
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _account_fingerprint(account: ContaContabil | ContaContabilEmpresa) -> str:
    return _fingerprint({field: getattr(account, field) for field in _COPIED_FIELDS})


def _record_item(
    session: Session,
    *,
    execution_id: str,
    link: EmpresaContaContabil,
    result: str,
    source: ContaContabil | None = None,
    identity: ContaContabilEmpresa | None = None,
    error_code: str | None = None,
) -> None:
    session.add(
        BackfillContasContabeisItem(
            execucao_id=execution_id,
            vinculo_legado_id=link.id,
            empresa_id=link.empresa_id,
            conta_codigo=link.conta_codigo,
            identidade_id=identity.id if identity is not None else None,
            resultado=result,
            source_fingerprint=(
                _account_fingerprint(source) if source is not None else None
            ),
            target_fingerprint=(
                _account_fingerprint(identity) if identity is not None else None
            ),
            error_code=error_code,
        )
    )
    session.commit()


def preflight_backfill(session: Session) -> BackfillResult:
    """Classify every legacy link without writing to the database."""
    eligible = already_present = conflicts = ineligible = 0
    links = session.execute(
        select(EmpresaContaContabil, ContaContabil)
        .outerjoin(
            ContaContabil,
            ContaContabil.codigo == EmpresaContaContabil.conta_codigo,
        )
        .order_by(EmpresaContaContabil.id)
    ).all()

    for link, source in links:
        if source is None:
            ineligible += 1
            continue
        identity = session.scalar(
            select(ContaContabilEmpresa).where(
                ContaContabilEmpresa.empresa_id == link.empresa_id,
                ContaContabilEmpresa.codigo == link.conta_codigo,
            )
        )
        if identity is None:
            eligible += 1
        elif _fields_match(identity, source):
            already_present += 1
        else:
            conflicts += 1

    return BackfillResult(
        eligible=eligible,
        already_present=already_present,
        conflicts=conflicts,
        ineligible=ineligible,
    )


def apply_backfill(session: Session) -> BackfillResult:
    """Apply eligible rows independently so a failed row can be retried safely."""
    execution_id = str(uuid4())
    execution = BackfillContasContabeisExecucao(id=execution_id, status="running")
    session.add(execution)
    session.commit()

    link_ids = session.scalars(
        select(EmpresaContaContabil.id).order_by(EmpresaContaContabil.id)
    ).all()
    for link_id in link_ids:
        try:
            link = session.get(EmpresaContaContabil, link_id)
            if link is None:
                continue
            source = session.scalar(
                select(ContaContabil).where(
                    ContaContabil.codigo == link.conta_codigo
                )
            )
            if source is None:
                _record_item(
                    session, execution_id=execution_id, link=link, result="ineligible"
                )
                continue

            identity = session.scalar(
                select(ContaContabilEmpresa).where(
                    ContaContabilEmpresa.empresa_id == link.empresa_id,
                    ContaContabilEmpresa.codigo == link.conta_codigo,
                )
            )
            if identity is not None:
                result = "already_present" if _fields_match(identity, source) else "conflict"
                _record_item(
                    session,
                    execution_id=execution_id,
                    link=link,
                    result=result,
                    source=source,
                    identity=identity,
                )
                continue

            identity = ContaContabilEmpresa(
                empresa_id=link.empresa_id,
                codigo=source.codigo,
                **{field: getattr(source, field) for field in _COPIED_FIELDS},
            )
            session.add(identity)
            session.flush()
            _record_item(
                session,
                execution_id=execution_id,
                link=link,
                result="created",
                source=source,
                identity=identity,
            )
        except SQLAlchemyError as exc:
            session.rollback()
            link = session.get(EmpresaContaContabil, link_id)
            if link is not None:
                source = session.scalar(
                    select(ContaContabil).where(
                        ContaContabil.codigo == link.conta_codigo
                    )
                )
                identity = session.scalar(
                    select(ContaContabilEmpresa).where(
                        ContaContabilEmpresa.empresa_id == link.empresa_id,
                        ContaContabilEmpresa.codigo == link.conta_codigo,
                    )
                )
                if (
                    isinstance(exc, IntegrityError)
                    and source is not None
                    and identity is not None
                ):
                    concurrent_result = (
                        "already_present"
                        if _fields_match(identity, source)
                        else "conflict"
                    )
                    _record_item(
                        session,
                        execution_id=execution_id,
                        link=link,
                        result=concurrent_result,
                        source=source,
                        identity=identity,
                    )
                    continue
                _record_item(
                    session,
                    execution_id=execution_id,
                    link=link,
                    result="failed",
                    source=source,
                    identity=identity,
                    error_code=type(exc).__name__,
                )

    execution = session.get(BackfillContasContabeisExecucao, execution_id)
    outcomes = session.scalars(
        select(BackfillContasContabeisItem.resultado).where(
            BackfillContasContabeisItem.execucao_id == execution_id
        )
    ).all()
    execution.status = "partial" if "failed" in outcomes else "completed"
    execution.completed_at = datetime.now(timezone.utc)
    session.commit()
    return BackfillResult(
        eligible=outcomes.count("created") + outcomes.count("failed"),
        already_present=outcomes.count("already_present"),
        conflicts=outcomes.count("conflict"),
        ineligible=outcomes.count("ineligible"),
        created=outcomes.count("created"),
        failed=outcomes.count("failed"),
        run_id=execution_id,
    )


def _has_identity_dependents(session: Session, identity_id: int) -> bool:
    connection = session.connection()
    inspector = inspect(connection)
    metadata = MetaData()
    for table_name in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(table_name):
            if foreign_key.get("referred_table") != "contas_contabeis_empresas":
                continue
            referred_columns = foreign_key.get("referred_columns") or []
            local_columns = foreign_key.get("constrained_columns") or []
            if "id" not in referred_columns or len(local_columns) != len(referred_columns):
                continue
            local_column = local_columns[referred_columns.index("id")]
            table = Table(table_name, metadata, autoload_with=connection)
            if connection.execute(
                select(table.c[local_column]).where(
                    table.c[local_column] == identity_id
                ).limit(1)
            ).first():
                return True
    return False


def rollback_backfill(session: Session, execution_id: str) -> BackfillResult:
    """Remove unchanged identities proven to belong to one execution only."""
    execution = session.get(BackfillContasContabeisExecucao, execution_id)
    if execution is None:
        raise ValueError("Execução de backfill não encontrada")

    items = session.scalars(
        select(BackfillContasContabeisItem)
        .where(
            BackfillContasContabeisItem.execucao_id == execution_id,
            BackfillContasContabeisItem.resultado == "created",
        )
        .order_by(BackfillContasContabeisItem.id)
    ).all()
    rolled_back = rollback_blocked = 0
    for item in items:
        if item.rollback_status == "rolled_back":
            rolled_back += 1
            continue
        if item.rollback_status == "blocked":
            rollback_blocked += 1
            continue

        identity = session.get(ContaContabilEmpresa, item.identidade_id)
        if identity is None:
            item.rollback_status = "rolled_back"
            session.commit()
            rolled_back += 1
            continue
        if (
            _account_fingerprint(identity) != item.target_fingerprint
            or _has_identity_dependents(session, identity.id)
        ):
            item.rollback_status = "blocked"
            session.commit()
            rollback_blocked += 1
            continue

        session.delete(identity)
        item.rollback_status = "rolled_back"
        session.commit()
        rolled_back += 1

    execution = session.get(BackfillContasContabeisExecucao, execution_id)
    execution.status = "rollback_partial" if rollback_blocked else "rolled_back"
    execution.rolled_back_at = datetime.now(timezone.utc)
    session.commit()
    return BackfillResult(
        rolled_back=rolled_back,
        rollback_blocked=rollback_blocked,
        run_id=execution_id,
    )


def _require_non_production_environment() -> None:
    app_environment = os.getenv("APP_ENV", "").strip().lower()
    if app_environment in {"prod", "production"}:
        raise RuntimeError("Backfill mutável bloqueado em ambiente de produção")
    if app_environment not in {"dev", "development", "test", "hml", "homologation"}:
        raise RuntimeError("Defina APP_ENV como dev, test ou hml para mutar dados")


def _result_payload(result: BackfillResult, mode: str) -> dict[str, object]:
    return {
        "mode": mode,
        "run_id": result.run_id,
        "eligible": result.eligible,
        "created": result.created,
        "already_present": result.already_present,
        "conflicts": result.conflicts,
        "ineligible": result.ineligible,
        "failed": result.failed,
        "rolled_back": result.rolled_back,
        "rollback_blocked": result.rollback_blocked,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preflight, apply, or selectively rollback company-account backfill."
    )
    parser.add_argument("mode", choices=("preflight", "apply", "rollback"))
    parser.add_argument("--run-id", help="Required execution id for rollback mode")
    args = parser.parse_args(argv)
    if args.mode == "rollback" and not args.run_id:
        parser.error("rollback requires --run-id")
    if args.mode != "preflight":
        try:
            _require_non_production_environment()
        except RuntimeError as exc:
            parser.error(str(exc))

    engine = create_engine(
        settings.DATABASE_URL,
        **build_engine_kwargs(settings.DATABASE_URL),
    )
    session_factory = sessionmaker(autoflush=False, bind=engine)
    try:
        with session_factory() as session:
            if args.mode == "preflight":
                result = preflight_backfill(session)
            elif args.mode == "apply":
                result = apply_backfill(session)
            else:
                result = rollback_backfill(session, args.run_id)
            print(json.dumps(_result_payload(result, args.mode), sort_keys=True))
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
