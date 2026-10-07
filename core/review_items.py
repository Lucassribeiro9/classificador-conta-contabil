from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import ReviewEvidence, ReviewItem, ReviewItemEvent


_CRITICALITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class ReviewItemNotFound(Exception):
    pass


class ReviewItemConflict(Exception):
    pass


def _get_item(session: Session, *, empresa_id: int, item_id: int) -> ReviewItem:
    item = session.scalar(
        select(ReviewItem)
        .where(ReviewItem.id == item_id, ReviewItem.empresa_id == empresa_id)
        .with_for_update()
    )
    if item is None:
        raise ReviewItemNotFound
    return item


def _record_transition(
    session: Session,
    *,
    item: ReviewItem,
    user_id: int,
    event_type: str,
    from_status: str | None,
    reason: str | None = None,
) -> None:
    transition = ReviewItemEvent(
        review_item_id=item.id,
        user_id=user_id,
        event_type=event_type,
        from_status=from_status,
        to_status=item.status,
        reason=reason,
    )
    session.add(transition)
    session.flush()
    record_audit_event(
        session,
        event_type=f"review_item.{event_type}",
        user_id=user_id,
        empresa_id=item.empresa_id,
        resource_id=str(item.id),
        metadata={
            "transition_id": transition.id,
            "from_status": from_status,
            "to_status": item.status,
        },
    )


def create_review_item(
    session: Session,
    *,
    empresa_id: int,
    source_type: str,
    grouping_key: str,
    summary: str,
    criticality: str,
    evidence: Iterable[dict[str, str]],
) -> ReviewItem:
    """Create or group a review item using the originating domain's explicit key."""
    if criticality not in _CRITICALITY_RANK:
        raise ValueError("Criticidade de pendência inválida")
    for value, name in (
        (source_type, "tipo de origem"),
        (grouping_key, "chave de agrupamento"),
        (summary, "resumo"),
    ):
        if not value or not value.strip():
            raise ValueError(f"{name.capitalize()} obrigatório")

    identity = (
        ReviewItem.empresa_id == empresa_id,
        ReviewItem.source_type == source_type,
        ReviewItem.grouping_key == grouping_key,
    )
    item = session.scalar(select(ReviewItem).where(*identity).with_for_update())
    if item is None:
        item = ReviewItem(
            empresa_id=empresa_id,
            source_type=source_type,
            grouping_key=grouping_key,
            summary=summary.strip(),
            criticality=criticality,
        )
        try:
            with session.begin_nested():
                session.add(item)
                session.flush()
        except IntegrityError:
            item = session.scalar(select(ReviewItem).where(*identity).with_for_update())
            if item is None:
                raise

    if _CRITICALITY_RANK[criticality] > _CRITICALITY_RANK[item.criticality]:
        item.criticality = criticality

    for evidence_item in evidence:
        source_evidence_type = evidence_item.get("source_type", "").strip()
        source_id = evidence_item.get("source_id", "").strip()
        evidence_summary = evidence_item.get("summary", "").strip()
        if not source_evidence_type or not source_id or not evidence_summary:
            raise ValueError("Evidência exige origem, identificador e resumo seguro")

        exists = session.scalar(
            select(ReviewEvidence.id).where(
                ReviewEvidence.review_item_id == item.id,
                ReviewEvidence.source_type == source_evidence_type,
                ReviewEvidence.source_id == source_id,
            )
        )
        if exists is None:
            session.add(
                ReviewEvidence(
                    review_item_id=item.id,
                    source_type=source_evidence_type,
                    source_id=source_id,
                    summary=evidence_summary,
                    safe_metadata={},
                )
            )

    session.flush()
    return item


def claim_review_item(
    session: Session, *, empresa_id: int, item_id: int, user_id: int
) -> ReviewItem:
    """Atomically claim a pending item; competing claims cannot both succeed."""
    result = session.execute(
        update(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.status == "pending",
            ReviewItem.assignee_id.is_(None),
        )
        .values(
            status="in_review",
            assignee_id=user_id,
            claimed_at=datetime.now(),
            updated_at=datetime.now(),
        )
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount != 1:
        item = session.scalar(
            select(ReviewItem).where(
                ReviewItem.id == item_id, ReviewItem.empresa_id == empresa_id
            )
        )
        if item is None:
            raise ReviewItemNotFound
        raise ReviewItemConflict("Pendência já assumida ou não está pendente")

    item = session.scalar(
        select(ReviewItem).where(ReviewItem.id == item_id)
    )
    transition = ReviewItemEvent(
        review_item_id=item_id,
        user_id=user_id,
        event_type="claimed",
        from_status="pending",
        to_status="in_review",
    )
    session.add(transition)
    session.flush()
    record_audit_event(
        session,
        event_type="review_item.claimed",
        user_id=user_id,
        empresa_id=empresa_id,
        resource_id=str(item_id),
        metadata={
            "transition_id": transition.id,
            "from_status": "pending",
            "to_status": "in_review",
        },
    )
    session.flush()
    return item


def release_review_item(
    session: Session, *, empresa_id: int, item_id: int, user_id: int
) -> ReviewItem:
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    result = session.execute(
        update(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.status == "in_review",
            ReviewItem.assignee_id == user_id,
        )
        .values(
            status="pending", assignee_id=None, claimed_at=None, updated_at=datetime.now()
        )
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount != 1:
        raise ReviewItemConflict("Somente a pessoa responsável pode liberar o claim")
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    _record_transition(
        session,
        item=item,
        user_id=user_id,
        event_type="released",
        from_status="in_review",
    )
    session.flush()
    return item


def reassign_review_item(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    actor_id: int,
    assignee_id: int,
    reason: str,
) -> ReviewItem:
    if not reason.strip():
        raise ValueError("Justificativa obrigatória")
    current_item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    previous_assignee_id = current_item.assignee_id
    if previous_assignee_id is None:
        raise ReviewItemConflict("A pendência não possui pessoa responsável")
    result = session.execute(
        update(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.status == "in_review",
            ReviewItem.assignee_id == previous_assignee_id,
        )
        .values(
            assignee_id=assignee_id,
            claimed_at=datetime.now(),
            updated_at=datetime.now(),
        )
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount != 1:
        raise ReviewItemConflict("Somente pendências em revisão podem ser reatribuídas")
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    _record_transition(
        session,
        item=item,
        user_id=actor_id,
        event_type="reassigned",
        from_status="in_review",
        reason=reason.strip(),
    )
    session.flush()
    return item


def resolve_review_item(
    session: Session, *, empresa_id: int, item_id: int, user_id: int
) -> ReviewItem:
    return _finish_review_item(
        session,
        empresa_id=empresa_id,
        item_id=item_id,
        user_id=user_id,
        status="resolved",
        event_type="resolved",
    )


def dismiss_review_item(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    user_id: int,
    reason: str,
) -> ReviewItem:
    if not reason.strip():
        raise ValueError("Justificativa obrigatória")
    return _finish_review_item(
        session,
        empresa_id=empresa_id,
        item_id=item_id,
        user_id=user_id,
        status="dismissed",
        event_type="dismissed",
        reason=reason.strip(),
    )


def _finish_review_item(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    user_id: int,
    status: str,
    event_type: str,
    reason: str | None = None,
) -> ReviewItem:
    _get_item(session, empresa_id=empresa_id, item_id=item_id)
    result = session.execute(
        update(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.status == "in_review",
            ReviewItem.assignee_id == user_id,
        )
        .values(
            status=status,
            assignee_id=None,
            claimed_at=None,
            resolved_at=datetime.now() if status == "resolved" else None,
            dismissed_at=datetime.now() if status == "dismissed" else None,
            updated_at=datetime.now(),
        )
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount != 1:
        raise ReviewItemConflict("A pendência deve estar assumida por quem a conclui")
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    _record_transition(
        session,
        item=item,
        user_id=user_id,
        event_type=event_type,
        from_status="in_review",
        reason=reason,
    )
    session.flush()
    return item


def reopen_review_item(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    user_id: int,
    reason: str,
) -> ReviewItem:
    if not reason.strip():
        raise ValueError("Justificativa obrigatória")
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    previous_status = item.status
    result = session.execute(
        update(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.status.in_(("resolved", "dismissed")),
        )
        .values(
            status="pending",
            assignee_id=None,
            claimed_at=None,
            resolved_at=None,
            dismissed_at=None,
            updated_at=datetime.now(),
        )
        .execution_options(synchronize_session="fetch")
    )
    if result.rowcount != 1:
        raise ReviewItemConflict("Somente pendências finalizadas podem ser reabertas")
    item = _get_item(session, empresa_id=empresa_id, item_id=item_id)
    _record_transition(
        session,
        item=item,
        user_id=user_id,
        event_type="reopened",
        from_status=previous_status,
        reason=reason.strip(),
    )
    session.flush()
    return item
