"""PostgreSQL-backed ML job admission and lifecycle."""

from hashlib import sha256
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import and_, case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.models import Empresa, MLJob


class IdempotencyConflict(ValueError):
    pass


@dataclass(frozen=True)
class ClaimedMLJob:
    id: int
    company_id: int
    kind: str
    lease_token: str
    attempt: int


def enqueue_ml_job(
    session: Session, *, company_id: int, kind: str,
    idempotency_key: str, payload: dict, requested_by: int | None = None,
) -> MLJob:
    if kind not in {"train", "classify", "classify_movements"}:
        raise ValueError("Tipo de job invalido")
    if not 1 <= len(idempotency_key) <= 128:
        raise ValueError("Chave de idempotencia invalida")
    canonical = json.dumps({"kind": kind, "payload": payload}, sort_keys=True, separators=(",", ":"))
    payload_hash = sha256(canonical.encode()).hexdigest()
    existing = session.scalar(select(MLJob).where(
        MLJob.empresa_id == company_id, MLJob.idempotency_key == idempotency_key,
    ))
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise IdempotencyConflict("Chave de idempotencia usada com outro payload")
        return existing
    try:
        with session.begin_nested():
            job = MLJob(
                empresa_id=company_id, kind=kind, pool="ml/cpu",
                requested_by=requested_by,
                idempotency_key=idempotency_key, payload_hash=payload_hash,
                payload=payload, status="queued", progress=0,
            )
            session.add(job)
            session.flush()
        return job
    except IntegrityError:
        existing = session.scalar(select(MLJob).where(
            MLJob.empresa_id == company_id,
            MLJob.idempotency_key == idempotency_key,
        ))
        if existing is None:
            raise
        if existing.payload_hash != payload_hash:
            raise IdempotencyConflict("Chave de idempotencia usada com outro payload")
        return existing


def claim_next_ml_job(
    sessions, *, worker_id: str, lease_seconds: int = 600,
    max_attempts: int = 2, now: datetime | None = None,
) -> ClaimedMLJob | None:
    """Serialize claims per company in PostgreSQL; recover expired leases."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    with sessions.begin() as session:
        skipped_company_ids: list[int] = []
        while True:
            job = session.scalar(
                select(MLJob).where(
                    or_(
                        MLJob.status == "queued",
                        and_(MLJob.status == "running", MLJob.lease_expires_at <= now),
                    ),
                    MLJob.empresa_id.notin_(skipped_company_ids),
                ).order_by(case((MLJob.status == "running", 0), else_=1),
                           MLJob.created_at, MLJob.id)
                .with_for_update(skip_locked=True).limit(1)
            )
            if job is None:
                break
            skipped_company_ids.append(job.empresa_id)
            locked_company = session.scalar(
                select(Empresa.id).where(Empresa.id == job.empresa_id)
                .with_for_update(skip_locked=True)
            )
            if locked_company is None:
                continue
            other_running = session.scalar(select(MLJob.id).where(
                MLJob.empresa_id == job.empresa_id,
                MLJob.id != job.id,
                MLJob.status == "running",
                MLJob.lease_expires_at > now,
            ).limit(1))
            if other_running is not None:
                continue
            if job.cancel_requested:
                job.status = "cancelled"
                job.lease_token = None
                job.lease_owner = None
                job.lease_expires_at = None
                continue
            if job.attempts >= max_attempts:
                job.status = "failed"
                job.error_code = "attempts_exhausted"
                job.lease_token = None
                job.lease_owner = None
                job.lease_expires_at = None
                continue
            token = str(uuid4())
            job.status = "running"
            job.attempts += 1
            job.lease_token = token
            job.lease_owner = worker_id
            job.lease_expires_at = now + timedelta(seconds=lease_seconds)
            job.progress = 5
            session.flush()
            return ClaimedMLJob(job.id, job.empresa_id, job.kind, token, job.attempts)
    return None
