"""Idempotência concorrente do envio manual no banco real."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.models import (
    Empresa,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    ReviewItem,
    Usuario,
)
from core.movimentos_operacionais_review_submission import submit_movement_for_review


pytestmark = pytest.mark.integration_postgres


def test_concurrent_submissions_create_one_review_item():
    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url.startswith("postgresql"), (
        "DATABASE_URL deve apontar para PostgreSQL"
    )
    engine = create_engine(database_url)
    suffix = uuid4().hex[:12]
    try:
        with Session(engine) as session:
            empresa = Empresa(
                nome_empresa="Empresa de teste de concorrência",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                api_key=f"api-review-{suffix}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            user = Usuario(
                nome="Operador de teste",
                login=f"operador-review-{suffix}",
                email=f"operador-review-{suffix}@example.com",
                senha_hash="hash-de-teste",
                papel="operador",
                is_active=True,
            )
            lote = LoteImportacaoMovimentoOperacional(
                empresa=empresa,
                usuario=user,
                original_filename="sintetico.xlsx",
                file_hash=f"sha256:review-{suffix}",
                status="completed",
                periodo_inicio=date(2026, 1, 1),
                periodo_fim=date(2026, 1, 31),
                cnpj_cpf_arquivo=empresa.cnpj_cpf,
            )
            movement = MovimentoOperacionalImportado(
                lote=lote,
                empresa=empresa,
                data=date(2026, 1, 2),
                conta_financeira=10046,
                historico="Histórico sintético",
                historico_normalizado="historico sintetico",
                valor_original=Decimal("-1.00"),
                valor_absoluto=Decimal("1.00"),
                direcao="credito",
                status="revisao",
            )
            session.add(movement)
            session.commit()
            empresa_id, lote_id, movement_id, user_id = (
                empresa.id,
                lote.id,
                movement.id,
                user.id,
            )

        barrier = Barrier(2)

        def submit() -> dict:
            with Session(engine) as session:
                barrier.wait()
                result = submit_movement_for_review(
                    session,
                    empresa_id=empresa_id,
                    lote_id=lote_id,
                    movimento_id=movement_id,
                    user_id=user_id,
                )
                session.commit()
                return result

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: submit(), range(2)))

        assert {result["outcome"] for result in results} == {"created", "existing"}
        assert results[0]["review_item_id"] == results[1]["review_item_id"]
        with Session(engine) as session:
            items = session.scalars(
                select(ReviewItem).where(
                    ReviewItem.empresa_id == empresa_id,
                    ReviewItem.source_type == "movimento_operacional_manual",
                )
            ).all()
            assert len(items) == 1
    finally:
        engine.dispose()
