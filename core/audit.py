from contextvars import ContextVar, Token
from typing import Any

from sqlalchemy.orm import Session

from core.models import AuditEvent


_audit_user_id: ContextVar[int | None] = ContextVar(
    "audit_user_id",
    default=None,
)
_audit_request_active: ContextVar[bool] = ContextVar(
    "audit_request_active",
    default=False,
)


def set_audit_user_id(user_id: int) -> Token:
    return _audit_user_id.set(user_id)


def begin_audit_request_context() -> None:
    _audit_request_active.set(True)
    clear_audit_context()


def end_audit_request_context() -> None:
    clear_audit_context()
    _audit_request_active.set(False)


def is_audit_request_context_active() -> bool:
    return _audit_request_active.get()


def get_audit_user_id() -> int | None:
    return _audit_user_id.get()


def clear_audit_context() -> None:
    _audit_user_id.set(None)


def record_audit_event(
    session: Session,
    *,
    event_type: str,
    user_id: int | None = None,
    empresa_id: int | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        user_id=user_id if user_id is not None else get_audit_user_id(),
        empresa_id=empresa_id,
        resource_id=resource_id,
        metadata_json=metadata or {},
    )
    session.add(event)
    return event
