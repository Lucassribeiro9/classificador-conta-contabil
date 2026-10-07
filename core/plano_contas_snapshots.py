"""Importação temporal do plano de contas no contexto de uma empresa."""

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import (
    PlanoContasConflictDecision,
    PlanoContasImportEvent,
    PlanoContasSnapshot,
    PlanoContasSnapshotEntry,
    ContaContabilEmpresa,
    Empresa,
    ReviewItem,
)
from core.review_items import (
    ReviewItemConflict,
    create_review_item,
    resolve_review_item,
)


class SnapshotConflict(Exception):
    """A vigência tem múltiplas interpretações ainda não resolvidas."""


@dataclass(frozen=True)
class ImportResult:
    snapshot: PlanoContasSnapshot
    evento: PlanoContasImportEvent
    review_item_id: int | None


def _digest(value: object) -> str:
    return sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _normalize(contas: list[dict]) -> list[dict]:
    if not contas:
        raise ValueError("Plano de contas vazio")
    normalized = []
    seen = set()
    for raw in contas:
        try:
            codigo, grau = int(raw["codigo"]), int(raw["grau"])
            item = {
                "codigo": codigo,
                "classificacao": str(raw["classificacao"]).strip(),
                "nome": str(raw["nome"]).strip(),
                "tipo": str(raw["tipo"]).strip().upper(),
                "grau": grau,
            }
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Conta inválida no plano") from exc
        if (
            codigo in seen
            or not item["classificacao"]
            or not item["nome"]
            or item["tipo"] not in {"A", "S"}
            or len(item["classificacao"]) > 80
            or len(item["nome"]) > 255
        ):
            raise ValueError("Conta inválida ou código duplicado no plano")
        seen.add(codigo)
        normalized.append(item)
    return sorted(normalized, key=lambda item: item["codigo"])


def _candidate_ids(session: Session, *, empresa_id: int, vigencia: date) -> list[int]:
    return sorted(
        set(
            session.scalars(
                select(PlanoContasImportEvent.snapshot_id).where(
                    PlanoContasImportEvent.empresa_id == empresa_id,
                    PlanoContasImportEvent.vigencia == vigencia,
                )
            ).all()
        )
    )


def _candidate_hash(ids: list[int]) -> str:
    return _digest(ids)


def importar_snapshot(
    session: Session,
    *,
    empresa_id: int,
    contas: list[dict],
    vigencia: date | None,
    origem: str,
) -> ImportResult:
    if not empresa_id:
        raise ValueError("empresa_id obrigatório")
    if not origem or not origem.strip() or len(origem) > 255:
        raise ValueError("Origem obrigatória e limitada a 255 caracteres")
    content = _normalize(contas)
    # PostgreSQL serializes all imports of the same company, including distinct
    # content at the same effective date. Both transactions then see the conflict.
    empresa = session.scalar(
        select(Empresa).where(Empresa.id == empresa_id).with_for_update()
    )
    if empresa is None:
        raise ValueError("Empresa não encontrada")
    content_hash = _digest(content)
    snapshot = session.scalar(
        select(PlanoContasSnapshot).where(
            PlanoContasSnapshot.empresa_id == empresa_id,
            PlanoContasSnapshot.content_hash == content_hash,
        )
    )
    if snapshot is None:
        try:
            with session.begin_nested():
                snapshot = PlanoContasSnapshot(
                    empresa_id=empresa_id, content_hash=content_hash, content=content
                )
                session.add(snapshot)
                session.flush()
        except IntegrityError:
            snapshot = session.scalar(
                select(PlanoContasSnapshot).where(
                    PlanoContasSnapshot.empresa_id == empresa_id,
                    PlanoContasSnapshot.content_hash == content_hash,
                )
            )
            if snapshot is None:
                raise

    existing_entries = session.scalar(
        select(PlanoContasSnapshotEntry.id)
        .where(PlanoContasSnapshotEntry.snapshot_id == snapshot.id)
        .limit(1)
    )
    if existing_entries is None:
        for account in content:
            identity = session.scalar(
                select(ContaContabilEmpresa).where(
                    ContaContabilEmpresa.empresa_id == empresa_id,
                    ContaContabilEmpresa.codigo == account["codigo"],
                )
            )
            if identity is None:
                identity = ContaContabilEmpresa(empresa_id=empresa_id, **account)
                session.add(identity)
                session.flush()
            session.add(
                PlanoContasSnapshotEntry(
                    snapshot_id=snapshot.id,
                    empresa_id=empresa_id,
                    conta_contabil_empresa_id=identity.id,
                    **account,
                )
            )
        session.flush()

    evento = PlanoContasImportEvent(
        empresa_id=empresa_id,
        snapshot_id=snapshot.id,
        vigencia=vigencia or date.today(),
        vigencia_inferida=vigencia is None,
        origem=origem.strip(),
    )
    session.add(evento)
    session.flush()
    ids = _candidate_ids(session, empresa_id=empresa_id, vigencia=evento.vigencia)
    review_item_id = None
    if len(ids) > 1:
        candidates = _candidate_hash(ids)
        decision = session.scalar(
            select(PlanoContasConflictDecision).where(
                PlanoContasConflictDecision.empresa_id == empresa_id,
                PlanoContasConflictDecision.vigencia == evento.vigencia,
                PlanoContasConflictDecision.candidate_hash == candidates,
            )
        )
        if decision is None:
            item = create_review_item(
                session,
                empresa_id=empresa_id,
                source_type="snapshot_conflict",
                grouping_key=f"{evento.vigencia.isoformat()}:{candidates}",
                summary=f"Conflito de vigência do plano em {evento.vigencia.isoformat()}",
                criticality="high",
                evidence=[
                    {
                        "source_type": "snapshot",
                        "source_id": str(i),
                        "summary": "Snapshot concorrente",
                    }
                    for i in ids
                ],
            )
            review_item_id = item.id
    record_audit_event(
        session,
        event_type="plan.snapshot_imported",
        empresa_id=empresa_id,
        resource_id=str(evento.id),
        metadata={
            "snapshot_id": snapshot.id,
            "vigencia_inferida": evento.vigencia_inferida,
            "review_item_id": review_item_id,
        },
    )
    return ImportResult(snapshot, evento, review_item_id)


def selecionar_snapshot(
    session: Session, *, empresa_id: int, competencia: date
) -> PlanoContasSnapshot | None:
    if not empresa_id:
        raise ValueError("empresa_id obrigatório")
    latest = session.scalar(
        select(PlanoContasImportEvent.vigencia)
        .where(
            PlanoContasImportEvent.empresa_id == empresa_id,
            PlanoContasImportEvent.vigencia <= competencia,
        )
        .order_by(PlanoContasImportEvent.vigencia.desc())
        .limit(1)
    )
    if latest is None:
        return None
    ids = _candidate_ids(session, empresa_id=empresa_id, vigencia=latest)
    if len(ids) == 1:
        return session.get(PlanoContasSnapshot, ids[0])
    decision = session.scalar(
        select(PlanoContasConflictDecision).where(
            PlanoContasConflictDecision.empresa_id == empresa_id,
            PlanoContasConflictDecision.vigencia == latest,
            PlanoContasConflictDecision.candidate_hash == _candidate_hash(ids),
        )
    )
    if decision is None:
        raise SnapshotConflict("Vigência com conflito pendente de revisão")
    return session.get(PlanoContasSnapshot, decision.selected_snapshot_id)


def resolver_conflito(
    session: Session,
    *,
    empresa_id: int,
    item_id: int,
    snapshot_id: int,
    user_id: int,
    reason: str,
) -> PlanoContasConflictDecision:
    if not reason.strip() or len(reason.strip()) > 500:
        raise ValueError("Justificativa obrigatória e limitada a 500 caracteres")
    item = session.scalar(
        select(ReviewItem)
        .where(
            ReviewItem.id == item_id,
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.source_type == "snapshot_conflict",
        )
        .with_for_update()
    )
    if item is None:
        raise ValueError("Pendência de snapshot não encontrada")
    try:
        vigencia_text, candidates = item.grouping_key.split(":", 1)
        vigencia = date.fromisoformat(vigencia_text)
    except ValueError as exc:
        raise ValueError("Pendência de snapshot inválida") from exc
    ids = _candidate_ids(session, empresa_id=empresa_id, vigencia=vigencia)
    if candidates != _candidate_hash(ids) or snapshot_id not in ids:
        raise ReviewItemConflict(
            "Candidatos mudaram ou snapshot não pertence ao conflito"
        )
    existing = session.scalar(
        select(PlanoContasConflictDecision).where(
            PlanoContasConflictDecision.empresa_id == empresa_id,
            PlanoContasConflictDecision.vigencia == vigencia,
            PlanoContasConflictDecision.candidate_hash == candidates,
        )
    )
    if existing:
        raise ReviewItemConflict("Conflito já resolvido")
    resolve_review_item(
        session,
        empresa_id=empresa_id,
        item_id=item_id,
        user_id=user_id,
        reason=reason.strip(),
    )
    decision = PlanoContasConflictDecision(
        empresa_id=empresa_id,
        vigencia=vigencia,
        candidate_hash=candidates,
        review_item_id=item_id,
        selected_snapshot_id=snapshot_id,
        user_id=user_id,
        reason=reason.strip(),
    )
    session.add(decision)
    session.flush()
    record_audit_event(
        session,
        event_type="plan.snapshot_conflict_resolved",
        user_id=user_id,
        empresa_id=empresa_id,
        resource_id=str(decision.id),
        metadata={
            "review_item_id": item_id,
            "selected_snapshot_id": snapshot_id,
            "candidate_ids": ids,
        },
    )
    return decision
