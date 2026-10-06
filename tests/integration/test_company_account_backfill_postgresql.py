"""Real PostgreSQL contract for the company-account backfill lifecycle."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.models import (
    BackfillContasContabeisExecucao,
    BackfillContasContabeisItem,
    ContaContabil,
    ContaContabilEmpresa,
    Empresa,
    EmpresaContaContabil,
)
from scripts.backfill_company_accounts import apply_backfill, preflight_backfill, rollback_backfill
from tests.integration.test_postgresql_integration import _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_postgresql_backfill_preflight_repeat_concurrency_and_rollback():
    engine = create_engine(_postgres_database_url())
    suffix = uuid4().hex[:10]
    code = 700_000_000 + int(suffix, 16) % 100_000_000
    with Session(engine) as session:
        company = Empresa(
            nome_empresa=f"Empresa backfill {suffix}",
            api_key=f"backfill-{suffix}",
            cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
            cod_dominio=int(suffix, 16) % 2_000_000_000,
        )
        account = ContaContabil(
            codigo=code,
            classificacao="1.1.1",
            nome="Conta sintética de teste",
            tipo="A",
            grau=3,
            is_active=True,
            is_financial_origin=True,
        )
        session.add_all([company, account])
        session.flush()
        link = EmpresaContaContabil(
            empresa_id=company.id,
            conta_codigo=account.codigo,
            quantidade_lancamentos=1,
            ultima_utilizacao=date(2026, 1, 31),
        )
        session.add(link)
        session.commit()
        company_id, account_id, link_id = company.id, account.id, link.id

    with Session(engine) as session:
        assert preflight_backfill(session).eligible == 1

    barrier = Barrier(2)

    def apply_concurrently():
        with Session(engine) as session:
            barrier.wait()
            return apply_backfill(session)

    run_ids: list[str | None] = []
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = [future.result() for future in (
                executor.submit(apply_concurrently),
                executor.submit(apply_concurrently),
            )]

        assert first.created + second.created == 1
        assert first.already_present + second.already_present == 1
        run_ids = [first.run_id, second.run_id]
        with Session(engine) as session:
            identities = session.scalars(
                select(ContaContabilEmpresa).where(
                    ContaContabilEmpresa.empresa_id == company_id,
                    ContaContabilEmpresa.codigo == code,
                )
            ).all()
            assert len(identities) == 1
            owner = first.run_id if first.created else second.run_id
            result = rollback_backfill(session, owner)
            assert result.rolled_back == 1
            assert session.scalars(
                select(ContaContabilEmpresa).where(
                    ContaContabilEmpresa.empresa_id == company_id,
                    ContaContabilEmpresa.codigo == code,
                )
            ).all() == []
    finally:
        with Session(engine) as session:
            session.query(BackfillContasContabeisItem).filter(
                BackfillContasContabeisItem.execucao_id.in_(run_ids)
            ).delete(synchronize_session=False)
            session.query(BackfillContasContabeisExecucao).filter(
                BackfillContasContabeisExecucao.id.in_(run_ids)
            ).delete(synchronize_session=False)
            session.query(EmpresaContaContabil).filter_by(id=link_id).delete()
            session.query(ContaContabil).filter_by(id=account_id).delete()
            session.query(Empresa).filter_by(id=company_id).delete()
            session.commit()
        engine.dispose()
