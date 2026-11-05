from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.dataset_builder import (
    _is_trainable_movimento,
    _valid_financial_origin_accounts,
    _valid_target_accounts,
)
from core.ml_engine import ClassificadorContabil
from core.models import (
    DatasetManifest,
    LoteImportacaoMovimentoOperacional,
    ModelVersion,
    MovimentoOperacionalImportado,
    PlanoContasImportEvent,
    PlanoContasSnapshot,
    PlanoContasSnapshotEntry,
    ReviewEvidence,
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
    movement_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Classifica movimentos operacionais pendentes de uma empresa.

    A classificacao usa o modelo treinado a partir do dataset canonico do Razao
    e persiste apenas sugestao, confianca e status. A decisao final continua
    dependendo de revisao humana.
    """
    query = (
        session.query(MovimentoOperacionalImportado)
        .filter(MovimentoOperacionalImportado.empresa_id == empresa_id)
        .filter(MovimentoOperacionalImportado.status == "pendente")
    )
    if movement_ids is not None:
        query = query.filter(MovimentoOperacionalImportado.id.in_(movement_ids))
    movimentos = query.order_by(MovimentoOperacionalImportado.id.asc()).all()
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
        if _has_critical_review(session, empresa_id, movimento.id):
            reason = "Há pendência crítica não resolvida para o movimento."
            _create_ml_review(
                session, movimento, reason=reason,
                snapshot_id=snapshot.id, context_date=context_date,
                context_source=context_source,
            )
            movimento.ml_suggestion_context = {
                "model_version_id": None,
                "snapshot_id": snapshot.id,
                "context_date": context_date.isoformat() if context_date else None,
                "context_source": context_source,
                "confidence": None,
                "alternatives": [],
                "historical_examples": [],
                "evidence": ["critical_review", "temporal_snapshot"],
                "abstention_reason": "critical_review_unresolved",
            }
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

    active_version = session.scalar(select(ModelVersion).where(
        ModelVersion.empresa_id == empresa_id,
        ModelVersion.status == "active",
    ))
    if active_version is None:
        for movimento, snapshot, _accounts, context_date, context_source in classifiable_movements:
            reason = "Não há versão ativa de modelo para sugerir contrapartida."
            _create_ml_review(
                session, movimento, reason=reason,
                snapshot_id=snapshot.id, context_date=context_date,
                context_source=context_source,
            )
            movimento.ml_suggestion_context = {
                "model_version_id": None,
                "snapshot_id": snapshot.id,
                "context_date": context_date.isoformat() if context_date else None,
                "context_source": context_source,
                "confidence": None,
                "alternatives": [],
                "historical_examples": [],
                "evidence": ["temporal_snapshot", "model_version_missing"],
                "abstention_reason": "model_version_missing",
            }
            movimento.status = "revisao"
            _append_validation_message(movimento, reason)
            total_revisao += 1
        result = _result(
            empresa_id=empresa_id, total_sugerido=0, total_revisao=total_revisao,
        )
        _audit_classification(session, result)
        session.flush()
        return result

    active_manifest = session.scalar(select(DatasetManifest).where(
        DatasetManifest.id == active_version.manifest_id,
        DatasetManifest.empresa_id == empresa_id,
    ))

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
        movimento.ml_suggestion_context = {
            "model_version_id": active_version.id,
            "snapshot_id": snapshot.id,
            "context_date": context_date.isoformat() if context_date else None,
            "context_source": context_source,
            "confidence": prediction["confidence_sugerida"],
            "alternatives": prediction.get("alternatives", []),
            "historical_examples": [],
            "evidence": ["model_probability", "temporal_snapshot", "company_account"],
        }
        predicted_account = prediction["contrapartida_sugerida"]
        if predicted_account is None or predicted_account not in valid_accounts:
            abstention_reason = prediction.get("abstention_reason", "predicted_account_outside_snapshot")
            reason = (
                "Confiança abaixo do threshold da versão ativa."
                if abstention_reason == "below_threshold"
                else "A previsão principal não pertence ao snapshot aplicável."
            )
            _create_ml_review(
                session,
                movimento,
                reason=reason,
                snapshot_id=snapshot.id,
                context_date=context_date,
                context_source=context_source,
            )
            movimento.ml_suggestion_context = {
                **movimento.ml_suggestion_context,
                "abstention_reason": abstention_reason,
            }
            movimento.contrapartida_sugerida = None
            movimento.confidence_sugerida = None
            movimento.status = "revisao"
            _append_validation_message(movimento, reason)
            total_revisao += 1
            continue
        movimento.ml_suggestion_context = {
            **movimento.ml_suggestion_context,
            "historical_examples": _historical_examples(
                session, empresa_id=empresa_id, account_code=predicted_account,
                snapshot_id=snapshot.id, valid_accounts=valid_accounts,
                exclude_movement_id=movimento.id,
                manifest_content=active_manifest.content if active_manifest else {},
            ),
        }
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


def _has_critical_review(session: Session, empresa_id: int, movement_id: int) -> bool:
    return session.scalar(
        select(ReviewItem.id)
        .join(ReviewEvidence, ReviewEvidence.review_item_id == ReviewItem.id)
        .where(
            ReviewItem.empresa_id == empresa_id,
            ReviewItem.criticality == "critical",
            ReviewItem.status != "resolved",
            ReviewEvidence.source_type == "movimento_operacional",
            ReviewEvidence.source_id == str(movement_id),
        )
        .limit(1)
    ) is not None


def _historical_examples(
    session: Session, *, empresa_id: int, account_code: int,
    snapshot_id: int, valid_accounts: set[int], exclude_movement_id: int,
    manifest_content: dict,
) -> list[dict]:
    candidates = session.scalars(
        select(MovimentoOperacionalImportado)
        .where(
            MovimentoOperacionalImportado.empresa_id == empresa_id,
            MovimentoOperacionalImportado.id != exclude_movement_id,
            MovimentoOperacionalImportado.status.in_(("aprovado", "corrigido")),
            MovimentoOperacionalImportado.elegivel_treino.is_(True),
            MovimentoOperacionalImportado.contrapartida_final == account_code,
        )
        .order_by(MovimentoOperacionalImportado.data.desc(),
                  MovimentoOperacionalImportado.id.desc())
        .limit(100)
    ).all()
    valid_company_accounts = _valid_target_accounts(
        session, empresa_id,
        [code for candidate in candidates for code in (
            candidate.conta_financeira, candidate.contrapartida_final,
            candidate.conta_debito, candidate.conta_credito,
        ) if code is not None],
    )
    financial_sources = _valid_financial_origin_accounts(
        session, empresa_id, [candidate.conta_financeira for candidate in candidates],
    )
    examples: list[dict] = []
    for candidate in candidates:
        if not _is_trainable_movimento(candidate):
            continue
        required_accounts = {
            candidate.conta_financeira, candidate.contrapartida_final,
            candidate.conta_debito, candidate.conta_credito,
        }
        if not required_accounts <= valid_accounts or not required_accounts <= valid_company_accounts:
            continue
        if candidate.conta_financeira not in financial_sources:
            continue
        try:
            candidate_snapshot = selecionar_snapshot(
                session, empresa_id=empresa_id, competencia=candidate.data,
            )
        except SnapshotConflict:
            continue
        if candidate_snapshot is None or candidate_snapshot.id != snapshot_id:
            continue
        if _has_critical_review(session, empresa_id, candidate.id):
            continue
        examples.append({
            "source_type": "movimento",
            "source_id": candidate.id,
            "movement_id": candidate.id,
            "account_code": account_code,
            "date": candidate.data.isoformat(),
            "history": candidate.historico_normalizado[:120],
        })
        if len(examples) == 3:
            break
    if len(examples) < 3:
        sources = manifest_content.get("sources", [])
        rows = manifest_content.get("rows", [])
        if isinstance(sources, list) and isinstance(rows, list) and len(sources) == len(rows):
            for source, row in zip(sources, rows):
                if not isinstance(source, dict) or not isinstance(row, dict):
                    continue
                if source.get("type") != "razao" or source.get("snapshot_id") != snapshot_id:
                    continue
                if row.get("target_conta_contrapartida") != account_code:
                    continue
                features = row.get("features")
                if not isinstance(features, str) or not isinstance(source.get("id"), int):
                    continue
                examples.append({
                    "source_type": "razao",
                    "source_id": source["id"],
                    "movement_id": None,
                    "account_code": account_code,
                    "date": None,
                    "history": features.split(" origem_", 1)[0][:120],
                })
                if len(examples) == 3:
                    break
    return examples


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


def _create_ml_review(
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
        source_type="movimento_operacional_ml",
        grouping_key=f"movimento:{movimento.id}",
        summary=f"Movimento {movimento.id}: {reason}",
        criticality="high",
        evidence=[{
            "source_type": "movimento_operacional",
            "source_id": str(movimento.id),
            "summary": reason,
        }],
    )
    source_evidence = session.scalar(select(ReviewEvidence).where(
        ReviewEvidence.review_item_id == item.id,
        ReviewEvidence.source_type == "movimento_operacional",
        ReviewEvidence.source_id == str(movimento.id),
    ))
    source_evidence.safe_metadata = {"lote_id": movimento.lote_id}
    _audit_temporal_context(
        session, movimento, snapshot_id=snapshot_id,
        context_date=context_date, context_source=context_source,
        reason="ml_abstention", review_item_id=item.id,
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
    active_id = session.scalar(
        select(ModelVersion.id).where(
            ModelVersion.empresa_id == result["empresa_id"],
            ModelVersion.status == "active",
        )
    )
    record_audit_event(
        session,
        event_type="operational_movements.classified",
        empresa_id=result["empresa_id"],
        resource_id="operational_movements_classification",
        metadata={
            "total_processado": result["quantidade_processada"],
            "total_sugerido": result["total_sugerido"],
            "total_revisao": result["total_revisao"],
            **({"model_version_id": active_id} if active_id else {}),
        },
    )
