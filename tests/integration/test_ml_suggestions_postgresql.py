"""Persisted ML abstention and review in real PostgreSQL."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.models import MovimentoOperacionalImportado, ReviewItem
from core.movimentos_operacionais_classification import classificar_movimentos_operacionais_pendentes
from tests.integration.test_postgresql_integration import _postgres_database_url
from tests.test_movimentos_operacionais_classification import (
    _empresa, _import_classification_snapshot, _lote, _movimento,
    _train_razao_dataset_model, _usuario,
)

pytestmark = pytest.mark.integration_postgres


def test_abstention_and_review_survive_postgresql_transaction(tmp_path):
    engine = create_engine(_postgres_database_url())
    try:
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                    empresa = _empresa()
                    usuario = _usuario()
                    movimento = _movimento(
                        _lote(empresa, usuario), empresa, status="pendente",
                        historico_normalizado="pagamento fornecedor sintético",
                    )
                    session.add(movimento)
                    _import_classification_snapshot(session, empresa)
                    session.commit()
                    _train_razao_dataset_model(
                        session, tmp_path, empresa.id, threshold=1.0,
                    )
                    result = classificar_movimentos_operacionais_pendentes(
                        session, empresa_id=empresa.id, model_dir=tmp_path,
                    )
                    session.commit()
                    assert result["total_revisao"] == 1
                    movement_id = movimento.id
                    company_id = empresa.id

                with Session(bind=connection, join_transaction_mode="create_savepoint") as verify:
                    stored = verify.get(MovimentoOperacionalImportado, movement_id)
                    review = verify.scalar(select(ReviewItem).where(
                        ReviewItem.empresa_id == company_id,
                        ReviewItem.source_type == "movimento_operacional_ml",
                        ReviewItem.grouping_key == f"movimento:{movement_id}",
                    ))
                    assert stored.contrapartida_sugerida is None
                    assert stored.contrapartida_final is None
                    assert stored.ml_suggestion_context["abstention_reason"] == "below_threshold"
                    assert review is not None and review.status == "pending"
                    assert review.evidences[0].safe_metadata == {"lote_id": stored.lote_id}
            finally:
                outer.rollback()
    finally:
        engine.dispose()
