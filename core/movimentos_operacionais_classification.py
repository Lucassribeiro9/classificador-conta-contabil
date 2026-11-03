from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.ml_engine import ClassificadorContabil
from core.models import (
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    PlanoContasImportEvent,
    PlanoContasSnapshot,
    PlanoContasSnapshotEntry,
    ReviewItem,
)
from core.plano_contas_snapshots import SnapshotConflict, selecionar_snapshot
from core.review_items import create_review_item


TEMPORAL_REVIEW_SOURCE = "movimento_operacional_temporal"


class MovimentoOperacionalModelNotFound(RuntimeError):
    """Indica ausencia de modelo treinado para classificar movimentos."""


def classificar_movimentos_operacionais_pendentes(
    session: Session,
    *,
    empresa_id: int,
    model_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Classifica movimentos operacionais pendentes de uma empresa.

    A classificacao usa o modelo treinado a partir do dataset canonico do Razao
    e persiste apenas sugestao, confianca e status. A decisao final continua
    dependendo de revisao humana.
    """
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .filter(MovimentoOperacionalImportado.empresa_id == empresa_id)
        .filter(MovimentoOperacionalImportado.status == "pendente")
        .order_by(MovimentoOperacionalImportado.id.asc())
        .all()
    )
    if not movimentos:
        result = _result(empresa_id=empresa_id, total_sugerido=0, total_revisao=0)
        _audit_classification(session, result)
        session.flush()
        return result

    classifiable_movements: list[
        tuple[
            MovimentoOperacionalImportado,
            PlanoContasSnapshot,
            set[int],
            Any,
            str,
        ]
    ] = []
    total_revisao = 0
    for movimento in movimentos:
        lote = session.get(LoteImportacaoMovimentoOperacional, movimento.lote_id)
        context_date = movimento.data
        context_source = "movement_date"
        if context_date is None:
            context_source = "batch_period_start_inferred"
            if lote is None:
                snapshot = None
                review_reason = "Não foi possível determinar o período do lote."
            else:
                context_date = lote.periodo_inicio
                snapshot = _snapshot_for_undated_movement(session, empresa_id, lote)
                review_reason = (
                    "O período do lote atravessa vigências sem data individual."
                    if snapshot is None
                    else ""
                )
        else:
            snapshot = None
        try:
            if context_source == "movement_date":
                snapshot = selecionar_snapshot(
                    session, empresa_id=empresa_id, competencia=context_date
                )
                review_reason = "Não há snapshot aplicável à data do movimento."
        except SnapshotConflict:
            snapshot = None
            review_reason = "Há conflito de snapshot na data do movimento."

        if snapshot is None:
            _create_temporal_review(
                session,
                movimento,
                reason=review_reason,
                snapshot_id=None,
                context_date=context_date,
                context_source=context_source,
            )
            movimento.status = "revisao"
            _append_validation_message(movimento, review_reason)
            total_revisao += 1
            continue

        valid_accounts = set(
            session.scalars(
                select(PlanoContasSnapshotEntry.codigo).where(
                    PlanoContasSnapshotEntry.snapshot_id == snapshot.id,
                    PlanoContasSnapshotEntry.empresa_id == empresa_id,
                    PlanoContasSnapshotEntry.tipo == "A",
                )
            ).all()
        )
        if movimento.conta_financeira not in valid_accounts:
            reason = "A conta financeira não é analítica no snapshot aplicável."
            _create_temporal_review(
                session,
                movimento,
                reason=reason,
                snapshot_id=snapshot.id,
                context_date=context_date,
                context_source=context_source,
            )
            movimento.status = "revisao"
            _append_validation_message(movimento, reason)
            total_revisao += 1
            continue
        classifiable_movements.append(
            (movimento, snapshot, valid_accounts, context_date, context_source)
        )

    if not classifiable_movements:
        result = _result(
            empresa_id=empresa_id,
            total_sugerido=0,
            total_revisao=total_revisao,
        )
        _audit_classification(session, result)
        session.flush()
        return result

    engine = ClassificadorContabil(session, model_dir=model_dir)
    if not engine.model_exists_for_company(empresa_id):
        record_audit_event(
            session,
            event_type="operational_movements.classification_failed",
            empresa_id=empresa_id,
            resource_id="operational_movements_classification",
            metadata={
                "total_pendentes": len(classifiable_movements),
                "error_type": "ModelNotFound",
                "reason": "model_not_found",
            },
        )
        session.flush()
        raise MovimentoOperacionalModelNotFound(
            "Modelo treinado não encontrado para a empresa"
        )

    predictions = engine.classify_operational_movements_from_saved_model(
        empresa_id=empresa_id,
        movimentos=[
            {
                "historico_normalizado": movimento.historico_normalizado,
                "conta_financeira": movimento.conta_financeira,
                "direcao": movimento.direcao,
                "tipo_movimento": movimento.tipo_movimento,
            }
            for movimento, _snapshot, _accounts, _context_date, _context_source in classifiable_movements
        ],
        allowed_target_accounts_by_movement=[
            accounts
            for _movement, _snapshot, accounts, _context_date, _context_source in classifiable_movements
        ],
    )

    total_sugerido = 0
    for (
        movimento,
        snapshot,
        valid_accounts,
        context_date,
        context_source,
    ), prediction in zip(classifiable_movements, predictions):
        predicted_account = prediction["contrapartida_sugerida"]
        if predicted_account is None or predicted_account not in valid_accounts:
            reason = (
                "O modelo não encontrou conta analítica aplicável no snapshot."
                if predicted_account is None
                else "A sugestão não pertence ao snapshot aplicável."
            )
            _create_temporal_review(
                session,
                movimento,
                reason=reason,
                snapshot_id=snapshot.id,
                context_date=context_date,
                context_source=context_source,
            )
            movimento.contrapartida_sugerida = None
            movimento.confidence_sugerida = None
            movimento.status = "revisao"
            _append_validation_message(movimento, reason)
            total_revisao += 1
            continue
        movimento.contrapartida_sugerida = predicted_account
        movimento.confidence_sugerida = prediction["confidence_sugerida"]
        movimento.status = prediction["status"]
        _audit_temporal_context(
            session,
            movimento,
            snapshot_id=snapshot.id,
            context_date=context_date,
            context_source=context_source,
        )
        if movimento.status == "sugerido":
            total_sugerido += 1
        else:
            total_revisao += 1

    result = _result(
        empresa_id=empresa_id,
        total_sugerido=total_sugerido,
        total_revisao=total_revisao,
    )
    _audit_classification(session, result)
    session.flush()
    return result


def _append_validation_message(
    movimento: MovimentoOperacionalImportado, message: str
) -> None:
    messages = list(movimento.mensagens_validacao or [])
    if message not in messages:
        messages.append(message)
    movimento.mensagens_validacao = messages


def _create_temporal_review(
    session: Session,
    movimento: MovimentoOperacionalImportado,
    *,
    reason: str,
    snapshot_id: int | None,
    context_date,
    context_source: str,
) -> ReviewItem:
    item = create_review_item(
        session,
        empresa_id=movimento.empresa_id,
        source_type=TEMPORAL_REVIEW_SOURCE,
        grouping_key=f"movimento:{movimento.id}",
        summary=(
            f"Movimento {movimento.id} em {context_date}: {reason}"
            + (f" Snapshot {snapshot_id}." if snapshot_id is not None else "")
        ),
        criticality="high",
        evidence=[
            {
                "source_type": "movimento_operacional",
                "source_id": str(movimento.id),
                "summary": f"Data {context_date}; {reason}",
            }
        ],
    )
    _audit_temporal_context(
        session,
        movimento,
        snapshot_id=snapshot_id,
        context_date=context_date,
        context_source=context_source,
        reason="temporal_review_required",
        review_item_id=item.id,
    )
    return item


def _snapshot_for_undated_movement(session, empresa_id: int, lote):
    """Use lot start only if all known validity changes keep one snapshot."""
    try:
        snapshot = selecionar_snapshot(
            session, empresa_id=empresa_id, competencia=lote.periodo_inicio
        )
    except SnapshotConflict:
        return None
    if snapshot is None:
        return None
    events = session.scalars(
        select(PlanoContasImportEvent)
        .where(
            PlanoContasImportEvent.empresa_id == empresa_id,
            PlanoContasImportEvent.vigencia > lote.periodo_inicio,
            PlanoContasImportEvent.vigencia <= lote.periodo_fim,
        )
        .order_by(PlanoContasImportEvent.vigencia.asc())
    ).all()
    for validity_date in sorted({event.vigencia for event in events}):
        try:
            at_date = selecionar_snapshot(
                session, empresa_id=empresa_id, competencia=validity_date
            )
        except SnapshotConflict:
            return None
        if at_date is None or at_date.id != snapshot.id:
            return None
    return snapshot


def _audit_temporal_context(
    session: Session,
    movimento: MovimentoOperacionalImportado,
    *,
    snapshot_id: int | None,
    context_date,
    context_source: str,
    reason: str | None = None,
    review_item_id: int | None = None,
) -> None:
    metadata = {
        "movement_id": movimento.id,
        "snapshot_id": snapshot_id,
        "context_date": context_date.isoformat() if context_date is not None else None,
        "context_source": context_source,
    }
    if reason is not None:
        metadata["reason"] = reason
    if review_item_id is not None:
        metadata["review_item_id"] = review_item_id
    record_audit_event(
        session,
        event_type="operational_movements.temporal_context_checked",
        empresa_id=movimento.empresa_id,
        resource_id=str(movimento.id),
        metadata=metadata,
    )


def _result(
    *,
    empresa_id: int,
    total_sugerido: int,
    total_revisao: int,
) -> dict[str, Any]:
    """Monta o resumo estavel da classificacao operacional."""
    quantidade_processada = total_sugerido + total_revisao
    return {
        "empresa_id": empresa_id,
        "quantidade_processada": quantidade_processada,
        "total_sugerido": total_sugerido,
        "total_revisao": total_revisao,
    }


def _audit_classification(session: Session, result: dict[str, Any]) -> None:
    """Registra auditoria sem historicos, documentos ou observacoes."""
    record_audit_event(
        session,
        event_type="operational_movements.classified",
        empresa_id=result["empresa_id"],
        resource_id="operational_movements_classification",
        metadata={
            "total_processado": result["quantidade_processada"],
            "total_sugerido": result["total_sugerido"],
            "total_revisao": result["total_revisao"],
        },
    )
