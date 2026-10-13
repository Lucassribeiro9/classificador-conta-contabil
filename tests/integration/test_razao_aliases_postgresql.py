"""Alias confirmation is scoped to the reviewed company's snapshot."""

from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.models import Empresa, RazaoAccountAlias, Usuario
from core.plano_contas_snapshots import importar_snapshot
from core.razao_aliases import confirmar_alias_razao
from core.review_items import ReviewItemNotFound, claim_review_item, create_review_item
from tests.integration.test_postgresql_integration import ROOT, _postgres_database_url


pytestmark = pytest.mark.integration_postgres


def test_confirmed_alias_is_persisted_only_for_reviewed_company_and_snapshot():
    url = _postgres_database_url()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    suffix = uuid4().hex[:10]
    try:
        with Session(engine) as session:
            companies = []
            for index in range(2):
                company = Empresa(
                    nome_empresa=f"Alias {suffix}-{index}",
                    api_key=f"alias-{suffix}-{index}",
                    cnpj_cpf=f"{(int(suffix, 16) + index) % 10**14:014d}",
                    cod_dominio=(int(suffix, 16) + index) % 2_000_000_000,
                )
                session.add(company)
                companies.append(company)
            user = Usuario(
                nome="Revisor teste",
                login=f"alias-review-{suffix}",
                email=f"alias-review-{suffix}@example.com",
                senha_hash="hash-de-teste",
                papel="contador",
            )
            session.add(user)
            session.flush()
            snapshots = [
                importar_snapshot(
                    session,
                    empresa_id=company.id,
                    contas=[{"codigo": 100, "classificacao": "1.1", "nome": "Banco", "tipo": "A", "grau": 2}],
                    vigencia=date(2026, 1, 1),
                    origem="teste",
                ).snapshot
                for company in companies
            ]
            item = create_review_item(
                session,
                empresa_id=companies[0].id,
                source_type="razao_account_unknown",
                grouping_key=f"{snapshots[0].id}:200",
                summary="Conta observada fora do snapshot",
                criticality="high",
                evidence=[{"source_type": "razao_line", "source_id": "1:1", "summary": "Lote 1, linha 1"}],
            )
            claim_review_item(session, empresa_id=companies[0].id, item_id=item.id, user_id=user.id)
            with pytest.raises(ReviewItemNotFound):
                confirmar_alias_razao(
                    session, empresa_id=companies[1].id, item_id=item.id,
                    target_codigo=100, user_id=user.id, reason="Contexto errado",
                )
            confirmar_alias_razao(
                session, empresa_id=companies[0].id, item_id=item.id,
                target_codigo=100, user_id=user.id, reason="Equivalência conferida",
            )
            session.commit()
            aliases = session.scalars(
                select(RazaoAccountAlias).where(
                    RazaoAccountAlias.empresa_id.in_([company.id for company in companies])
                )
            ).all()
            assert len(aliases) == 1
            assert aliases[0].empresa_id == companies[0].id
            assert aliases[0].snapshot_id == snapshots[0].id
            assert aliases[0].snapshot_id != snapshots[1].id
            with pytest.raises(IntegrityError):
                with session.begin_nested():
                    session.add(RazaoAccountAlias(
                        empresa_id=companies[1].id,
                        snapshot_id=snapshots[1].id,
                        observed_code=201,
                        target_codigo=999,
                        review_item_id=item.id,
                        user_id=user.id,
                        reason="Destino ausente",
                    ))
                    session.flush()
        with pytest.raises(RuntimeError, match="Confirmed aliases exist"):
            command.downgrade(config, "-1")
    finally:
        engine.dispose()
