from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_global_admin
from api.schemas import AuditEventListResponse, AuditEventResponse
from core.models import AuditEvent, Usuario


router = APIRouter(prefix="/admin/audit-events")


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: int | None = Query(None),
    empresa_id: int | None = Query(None),
    event_type: str | None = Query(None),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> AuditEventListResponse:
    """Lista eventos de auditoria para administradores globais."""
    query = db.query(AuditEvent)
    if user_id is not None:
        query = query.filter(AuditEvent.user_id == user_id)
    if empresa_id is not None:
        query = query.filter(AuditEvent.empresa_id == empresa_id)
    if event_type is not None:
        query = query.filter(AuditEvent.event_type == event_type)
    if data_inicio is not None:
        query = query.filter(
            AuditEvent.timestamp >= datetime.combine(data_inicio, time.min)
        )
    if data_fim is not None:
        query = query.filter(
            AuditEvent.timestamp <= datetime.combine(data_fim, time.max)
        )

    total = query.count()
    events = (
        query.order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return AuditEventListResponse(
        items=[
            AuditEventResponse(
                id=event.id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                user_id=event.user_id,
                empresa_id=event.empresa_id,
                resource_id=event.resource_id,
                metadata=event.metadata_json,
            )
            for event in events
        ],
        total=total,
        page=page,
        limit=limit,
        has_next=page * limit < total,
    )
