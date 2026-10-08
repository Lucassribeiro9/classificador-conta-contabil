"""Human confirmation of observed Razão codes within one company snapshot."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import PlanoContasSnapshotEntry, RazaoAccountAlias, ReviewItem
from core.review_items import ReviewItemConflict, ReviewItemNotFound, resolve_review_item


def confirmar_alias_razao(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    target_codigo: int,
    user_id: int,
    reason: str,
) -> RazaoAccountAlias:
    """Resolve a claimed unknown-account item and records one scoped mapping."""
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValueError("Justificativa obrigatória e limitada a 500 caracteres")
    item = session.scalar(
        select(ReviewItem).where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
        ).with_for_update()
    )
    if item is None:
        raise ReviewItemNotFound
    if item.source_type != "razao_account_unknown":
        raise ReviewItemConflict("Pendência não permite confirmação de alias")
    if item.status != "in_review" or item.assignee_id != user_id:
        raise ReviewItemConflict("A pendência deve estar assumida por quem confirma")
    try:
        snapshot_text, observed_text, *_ = item.grouping_key.split(":")
        snapshot_id, observed_code = int(snapshot_text), int(observed_text)
    except ValueError as exc:
        raise ReviewItemConflict("Contexto da pendência inválido") from exc
    target = session.scalar(
        select(PlanoContasSnapshotEntry.id).where(
            PlanoContasSnapshotEntry.snapshot_id == snapshot_id,
            PlanoContasSnapshotEntry.empresa_id == empresa_id,
            PlanoContasSnapshotEntry.codigo == target_codigo,
        )
    )
    if target is None or target_codigo == observed_code:
        raise ReviewItemConflict("Conta de destino não pertence ao snapshot ou não é alias")
    if session.scalar(select(RazaoAccountAlias.id).where(
        RazaoAccountAlias.empresa_id == empresa_id,
        RazaoAccountAlias.snapshot_id == snapshot_id,
        RazaoAccountAlias.observed_code == observed_code,
    )) is not None:
        raise ReviewItemConflict("Alias já confirmado neste snapshot")
    alias = RazaoAccountAlias(
        empresa_id=empresa_id,
        snapshot_id=snapshot_id,
        observed_code=observed_code,
        target_codigo=target_codigo,
        review_item_id=item_id,
        user_id=user_id,
        reason=reason,
    )
    session.add(alias)
    session.flush()
    resolve_review_item(
        session,
        empresa_id=empresa_id,
        item_id=item_id,
        user_id=user_id,
        reason=reason,
    )
    record_audit_event(
        session,
        event_type="razao.alias_confirmed",
        user_id=user_id,
        empresa_id=empresa_id,
        resource_id=str(alias.id),
        metadata={
            "snapshot_id": snapshot_id,
            "review_item_id": item_id,
        },
    )
    session.flush()
    return alias
