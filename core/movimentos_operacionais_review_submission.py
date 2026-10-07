"""Encaminhamento manual de movimentos à central de revisões."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import MovimentoOperacionalImportado, ReviewItem
from core.review_items import create_review_item


ELIGIBLE_STATUSES = {"pendente", "pre_classificado", "sugerido", "revisao"}
SOURCE_TYPE = "movimento_operacional_manual"


def submit_movement_for_review(
    db: Session, *, empresa_id: int, lote_id: int, movimento_id: int, user_id: int
) -> dict:
    """Retorna um resultado seguro por movimento sem alterar sua decisão."""
    movement = db.scalar(
        select(MovimentoOperacionalImportado)
        .where(
            MovimentoOperacionalImportado.id == movimento_id,
            MovimentoOperacionalImportado.empresa_id == empresa_id,
            MovimentoOperacionalImportado.lote_id == lote_id,
        )
        .with_for_update()
    )
    if movement is None:
        return _result(movimento_id, "not_found", "Movimento não encontrado neste lote")
    if movement.status not in ELIGIBLE_STATUSES:
        return _result(
            movimento_id, "ineligible", "Status não permite envio para revisão"
        )

    key = f"movimento:{movimento_id}"
    existing = db.scalar(
        select(ReviewItem)
        .where(
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.source_type == SOURCE_TYPE,
            ReviewItem.grouping_key == key,
        )
        .with_for_update()
    )
    if existing is not None:
        if existing.status in {"resolved", "dismissed"}:
            return _result(
                movimento_id,
                "closed",
                "Pendência já encerrada; o envio não a reabre",
                existing.id,
            )
        return _result(
            movimento_id, "existing", "Pendência aberta já existente", existing.id
        )

    item = create_review_item(
        db,
        empresa_id=empresa_id,
        source_type=SOURCE_TYPE,
        grouping_key=key,
        summary=f"Movimento operacional {movimento_id} enviado para revisão",
        criticality="medium",
        evidence=[
            {
                "source_type": "movimento_operacional",
                "source_id": str(movimento_id),
                "summary": "Envio manual para revisão",
            }
        ],
    )
    if item.status in {"resolved", "dismissed"}:
        return _result(
            movimento_id,
            "closed",
            "Pendência já encerrada; o envio não a reabre",
            item.id,
        )
    record_audit_event(
        db,
        event_type="operational_movements.review_submitted",
        user_id=user_id,
        empresa_id=empresa_id,
        resource_id=str(movimento_id),
        metadata={"review_item_id": item.id, "lote_id": lote_id},
    )
    return _result(movimento_id, "created", "Enviado para revisão", item.id)


def _result(
    movimento_id: int, outcome: str, message: str, review_item_id: int | None = None
) -> dict:
    return {
        "movimento_id": movimento_id,
        "outcome": outcome,
        "message": message,
        "review_item_id": review_item_id,
    }
