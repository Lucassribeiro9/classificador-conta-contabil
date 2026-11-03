from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from core.models import (
    ContaContabil,
    ContaContabilEmpresa,
    DatasetManifest,
    FeedbackClassificacao,
    LancamentoRazaoNormalizado,
    MovimentoOperacionalImportado,
    PlanoContasSnapshot,
    PlanoContasSnapshotEntry,
    RazaoAccountAlias,
    ReviewEvidence,
    ReviewItem,
)
from core.plano_contas_snapshots import SnapshotConflict, selecionar_snapshot


@dataclass(frozen=True)
class DatasetTreinoContrapartida:
    linhas: list[dict[str, Any]]
    metadata: dict[str, Any]
    manifesto: dict[str, Any] | None = None


PIPELINE_VERSION = "dataset-contrapartida-v2"


def _content_hash(content: dict[str, Any]) -> str:
    canonical = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def reconstruct_dataset_from_manifest(
    session: Session, *, empresa_id: int, manifest_id: int
) -> list[dict[str, Any]]:
    manifest = session.scalar(select(DatasetManifest).where(
        DatasetManifest.id == manifest_id,
        DatasetManifest.empresa_id == empresa_id,
    ))
    if manifest is None:
        raise ValueError("Manifesto não encontrado para a empresa")
    if _content_hash(manifest.content) != manifest.content_hash:
        raise ValueError("Integridade do manifesto inválida")
    return manifest.content["rows"]


def build_dataset_treino_contrapartida(
    session: Session,
    *,
    empresa_id: int | None,
) -> DatasetTreinoContrapartida:
    """Compose eligible company examples and persist their immutable manifest."""
    if empresa_id is None:
        raise ValueError("empresa_id e obrigatorio")

    lancamentos_empresa = session.query(LancamentoRazaoNormalizado).filter(
        LancamentoRazaoNormalizado.empresa_id == empresa_id
    )
    lancamentos_candidatos = lancamentos_empresa.order_by(
        LancamentoRazaoNormalizado.id.asc()
    ).all()
    movimentos_empresa = session.query(MovimentoOperacionalImportado).filter(
        MovimentoOperacionalImportado.empresa_id == empresa_id
    )
    movimentos = (
        movimentos_empresa.order_by(MovimentoOperacionalImportado.id.asc()).all()
    )
    origens = _company_accounts(
        session,
        empresa_id,
        [lancamento.conta_origem for lancamento in lancamentos_candidatos],
    )
    feedback_por_lancamento = _latest_feedback_by_lancamento(
        session,
        empresa_id=empresa_id,
        lancamento_ids=[lancamento.id for lancamento in lancamentos_candidatos],
    )
    contas_validas = _valid_target_accounts(
        session,
        empresa_id,
        [
            _target_for_lancamento(lancamento, feedback_por_lancamento)
            for lancamento in lancamentos_candidatos
        ],
    )
    linhas_razao = []
    snapshot_ids: set[int] = set()
    source_refs: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    critical_sources, review_refs = _review_context(
        session, empresa_id, lancamentos_candidatos, movimentos
    )
    for lancamento in lancamentos_candidatos:
        target = _target_for_lancamento(lancamento, feedback_por_lancamento)
        snapshot, temporal_reason = _resolve_snapshot(
            session, empresa_id, lancamento.data
        )
        if snapshot is not None:
            snapshot_ids.add(snapshot.id)
        origin = origens.get(lancamento.conta_origem)
        if temporal_reason is not None:
            reason = temporal_reason
        elif not (origin and origin.tipo == "A" and origin.is_active is True and origin.is_financial_origin is True):
            reason = "origin_invalid"
        elif target not in contas_validas:
            reason = "target_invalid"
        elif not _snapshot_has_accounts(
            session,
            empresa_id,
            snapshot.id,
            {
                lancamento.conta_origem,
                lancamento.conta_contrapartida,
                lancamento.conta_debito,
                lancamento.conta_credito,
                target,
            },
            allow_aliases=True,
        ):
            reason = "account_not_in_snapshot"
        elif _razao_has_critical_review(lancamento, critical_sources):
            reason = "critical_review_unresolved"
        else:
            reason = None

        if reason is not None:
            exclusions.append({"type": "razao", "id": lancamento.id, "reason": reason})
        else:
            linhas_razao.append(_to_dataset_row(lancamento, target=target))
            snapshot_ids.add(snapshot.id)
            source_refs.append({
                "type": "razao",
                "id": lancamento.id,
                "snapshot_id": snapshot.id,
                "feedback_id": feedback_por_lancamento[lancamento.id].id
                if lancamento.id in feedback_por_lancamento else None,
            })

    movement_rows, movement_exclusions = _dataset_rows_from_movimentos(
        session, empresa_id, movimentos, critical_sources
    )
    exclusions.extend(movement_exclusions)
    linhas_movimentos = [row for row, _movement_id, _snapshot_id in movement_rows]
    for _row, movement_id, snapshot_id in movement_rows:
        snapshot_ids.add(snapshot_id)
        source_refs.append({"type": "movimento", "id": movement_id, "snapshot_id": snapshot_id})
    for movimento in movimentos:
        snapshot = _snapshot_for_date(session, empresa_id, movimento.data)
        if snapshot is not None:
            snapshot_ids.add(snapshot.id)
    linhas = linhas_razao + linhas_movimentos
    contagem_por_target = _count_targets(linhas)
    total_descartes_razao = lancamentos_empresa.count() - len(linhas_razao)
    total_descartes_movimentos = movimentos_empresa.count() - len(linhas_movimentos)
    total_descartes = total_descartes_razao + total_descartes_movimentos
    treinavel = len(linhas) >= 10 and len(contagem_por_target) >= 2

    snapshots = session.scalars(select(PlanoContasSnapshot).where(
        PlanoContasSnapshot.empresa_id == empresa_id,
        PlanoContasSnapshot.id.in_(snapshot_ids),
    )).all()

    content = {
        "schema_version": 1,
        "pipeline_version": PIPELINE_VERSION,
        "empresa_id": empresa_id,
        "snapshots": sorted(snapshot_ids),
        "snapshot_hashes": [
            {"id": snapshot.id, "hash": snapshot.content_hash}
            for snapshot in sorted(snapshots, key=lambda item: item.id)
        ],
        "sources": source_refs,
        "source_hashes": [
            {"type": "razao", "id": item.id, "hash": _razao_source_hash(item, feedback_por_lancamento.get(item.id))}
            for item in lancamentos_candidatos
        ] + [
            {"type": "movimento", "id": item.id, "hash": _movement_source_hash(item)}
            for item in movimentos
        ],
        "reviews": review_refs,
        "exclusions": exclusions,
        "rules": ["temporal_snapshot", "validated_company_accounts", "final_human_decision"],
        "rows": linhas,
    }
    manifest = DatasetManifest(
        empresa_id=empresa_id, content_hash=_content_hash(content), content=content
    )
    session.add(manifest)
    session.flush()

    return DatasetTreinoContrapartida(
        linhas=linhas,
        metadata={
            "empresa_id": empresa_id,
            "total_linhas": len(linhas),
            "total_linhas_razao": len(linhas_razao),
            "total_linhas_movimentos": len(linhas_movimentos),
            "total_descartes": total_descartes,
            "total_descartes_razao": total_descartes_razao,
            "total_descartes_movimentos": total_descartes_movimentos,
            "contagem_por_target": contagem_por_target,
            "treinavel": treinavel,
        },
        manifesto={"id": manifest.id, "hash": manifest.content_hash, **content},
    )


def _to_dataset_row(
    lancamento: LancamentoRazaoNormalizado,
    *,
    target: int,
) -> dict[str, Any]:
    feature_tokens = [
        lancamento.historico_normalizado.strip(),
        f"origem_{lancamento.conta_origem}",
        f"direcao_{lancamento.direcao}",
    ]

    return {
        "features": " ".join(token for token in feature_tokens if token),
        "target_conta_contrapartida": target,
    }


def _dataset_rows_from_movimentos(
    session: Session,
    empresa_id: int,
    movimentos: list[MovimentoOperacionalImportado],
    critical_sources: set[tuple[str, str]],
) -> tuple[list[tuple[dict[str, Any], int, int]], list[dict[str, Any]]]:
    if not movimentos:
        return [], []

    valid_accounts = _valid_target_accounts(
        session,
        empresa_id,
        [
            codigo
            for movimento in movimentos
            for codigo in (
                movimento.conta_financeira,
                movimento.contrapartida_final,
                movimento.conta_debito,
                movimento.conta_credito,
            )
            if codigo is not None
        ],
    )
    financial_sources = _valid_financial_origin_accounts(
        session,
        empresa_id,
        [movimento.conta_financeira for movimento in movimentos],
    )

    rows = []
    exclusions = []
    for movimento in movimentos:
        required_accounts = {
            movimento.conta_financeira,
            movimento.contrapartida_final,
            movimento.conta_debito,
            movimento.conta_credito,
        }
        snapshot, temporal_reason = _resolve_snapshot(session, empresa_id, movimento.data)
        if movimento.status == "rejeitado":
            reason = "rejected"
        elif movimento.status not in {"aprovado", "corrigido"}:
            reason = "no_final_decision"
        elif not _is_trainable_movimento(movimento):
            reason = "incomplete_or_not_trainable"
        elif temporal_reason is not None:
            reason = temporal_reason
        elif not required_accounts.issubset(valid_accounts):
            reason = "account_invalid"
        elif movimento.conta_financeira not in financial_sources:
            reason = "origin_invalid"
        elif ("movimento_operacional", str(movimento.id)) in critical_sources:
            reason = "critical_review_unresolved"
        elif not _snapshot_has_accounts(session, empresa_id, snapshot.id, required_accounts):
            reason = "account_not_in_snapshot"
        else:
            reason = None
        if reason is not None:
            exclusions.append({"type": "movimento", "id": movimento.id, "reason": reason})
        else:
            rows.append((_to_dataset_row_from_movimento(movimento), movimento.id, snapshot.id))
    return rows, exclusions


def _is_trainable_movimento(movimento: MovimentoOperacionalImportado) -> bool:
    return (
        movimento.status in {"aprovado", "corrigido"}
        and movimento.elegivel_treino is True
        and movimento.contrapartida_final is not None
        and movimento.conta_debito is not None
        and movimento.conta_credito is not None
    )


def _to_dataset_row_from_movimento(
    movimento: MovimentoOperacionalImportado,
) -> dict[str, Any]:
    feature_tokens = [
        movimento.historico_normalizado.strip(),
        f"origem_{movimento.conta_financeira}",
        f"direcao_{movimento.direcao}",
    ]

    return {
        "features": " ".join(token for token in feature_tokens if token),
        "target_conta_contrapartida": movimento.contrapartida_final,
    }


def _target_for_lancamento(
    lancamento: LancamentoRazaoNormalizado,
    feedback_por_lancamento: dict[int, FeedbackClassificacao],
) -> int:
    feedback = feedback_por_lancamento.get(lancamento.id)
    return feedback.conta_final if feedback is not None else lancamento.conta_contrapartida


def _latest_feedback_by_lancamento(
    session: Session,
    *,
    empresa_id: int,
    lancamento_ids: list[int],
) -> dict[int, FeedbackClassificacao]:
    if not lancamento_ids:
        return {}

    feedbacks = (
        session.query(FeedbackClassificacao)
        .filter(FeedbackClassificacao.empresa_id == empresa_id)
        .filter(FeedbackClassificacao.lancamento_id.in_(lancamento_ids))
        .order_by(
            FeedbackClassificacao.lancamento_id.asc(),
            FeedbackClassificacao.created_at.asc(),
            FeedbackClassificacao.id.asc(),
        )
        .all()
    )
    latest: dict[int, FeedbackClassificacao] = {}
    for feedback in feedbacks:
        latest[feedback.lancamento_id] = feedback
    return latest


def _razao_source_hash(
    item: LancamentoRazaoNormalizado, feedback: FeedbackClassificacao | None
) -> str:
    return _content_hash({
        "id": item.id,
        "lote_id": item.lote_id,
        "linha_original": item.linha_original,
        "data": item.data.isoformat() if item.data else None,
        "origem": item.conta_origem,
        "contrapartida": item.conta_contrapartida,
        "debito": item.conta_debito,
        "credito": item.conta_credito,
        "historico": item.historico_normalizado,
        "direcao": item.direcao,
        "feedback_id": feedback.id if feedback else None,
        "feedback_conta": feedback.conta_final if feedback else None,
    })


def _movement_source_hash(item: MovimentoOperacionalImportado) -> str:
    return _content_hash({
        "id": item.id,
        "lote_id": item.lote_id,
        "data": item.data.isoformat() if item.data else None,
        "origem": item.conta_financeira,
        "contrapartida": item.contrapartida_final,
        "debito": item.conta_debito,
        "credito": item.conta_credito,
        "historico": item.historico_normalizado,
        "direcao": item.direcao,
        "status": item.status,
        "elegivel_treino": item.elegivel_treino,
        "row_version": item.row_version,
    })


def _valid_target_accounts(
    session: Session, empresa_id: int, targets: list[int]
) -> set[int]:
    if not targets:
        return set()

    contas = _company_accounts(session, empresa_id, targets)
    return {
        codigo
        for codigo, conta in contas.items()
        if conta.tipo == "A" and conta.is_active is True
    }


def _valid_financial_origin_accounts(
    session: Session, empresa_id: int, accounts: list[int]
) -> set[int]:
    if not accounts:
        return set()

    contas = _company_accounts(session, empresa_id, accounts)
    return {
        codigo
        for codigo, conta in contas.items()
        if (
            conta.tipo == "A"
            and conta.is_active is True
            and conta.is_financial_origin is True
        )
    }


def _company_accounts(
    session: Session, empresa_id: int, codigos: list[int]
) -> dict[int, ContaContabil | ContaContabilEmpresa]:
    """Identidade empresarial prevalece; catálogo global é fallback transitório."""
    requested = set(codigos)
    if not requested:
        return {}
    contas: dict[int, ContaContabil | ContaContabilEmpresa] = {
        conta.codigo: conta
        for conta in session.query(ContaContabil)
        .filter(ContaContabil.codigo.in_(requested))
        .all()
    }
    contas.update(
        {
            conta.codigo: conta
            for conta in session.query(ContaContabilEmpresa)
            .filter(ContaContabilEmpresa.empresa_id == empresa_id)
            .filter(ContaContabilEmpresa.codigo.in_(requested))
            .all()
        }
    )
    return contas


def _count_targets(linhas: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for linha in linhas:
        target = linha["target_conta_contrapartida"]
        counts[target] = counts.get(target, 0) + 1
    return counts


def _snapshot_for_date(session: Session, empresa_id: int, context_date):
    return _resolve_snapshot(session, empresa_id, context_date)[0]


def _resolve_snapshot(session: Session, empresa_id: int, context_date):
    if context_date is None:
        return None, "temporal_context_missing"
    try:
        snapshot = selecionar_snapshot(
            session, empresa_id=empresa_id, competencia=context_date
        )
    except SnapshotConflict:
        return None, "snapshot_conflict"
    return (snapshot, None) if snapshot is not None else (None, "snapshot_missing")


def _snapshot_has_accounts(
    session: Session,
    empresa_id: int,
    snapshot_id: int,
    codes: set[int],
    *,
    allow_aliases: bool = False,
) -> bool:
    found = set(session.scalars(select(PlanoContasSnapshotEntry.codigo).where(
        PlanoContasSnapshotEntry.empresa_id == empresa_id,
        PlanoContasSnapshotEntry.snapshot_id == snapshot_id,
        PlanoContasSnapshotEntry.codigo.in_(codes),
        PlanoContasSnapshotEntry.tipo == "A",
    )).all())
    missing = codes - found
    if missing and allow_aliases:
        aliases = session.scalars(
            select(RazaoAccountAlias.observed_code)
            .join(
                PlanoContasSnapshotEntry,
                and_(
                    PlanoContasSnapshotEntry.snapshot_id == RazaoAccountAlias.snapshot_id,
                    PlanoContasSnapshotEntry.empresa_id == RazaoAccountAlias.empresa_id,
                    PlanoContasSnapshotEntry.codigo == RazaoAccountAlias.target_codigo,
                    PlanoContasSnapshotEntry.tipo == "A",
                ),
            )
            .where(
                RazaoAccountAlias.empresa_id == empresa_id,
                RazaoAccountAlias.snapshot_id == snapshot_id,
                RazaoAccountAlias.observed_code.in_(missing),
            )
        ).all()
        found.update(aliases)
    return codes <= found


def _review_context(
    session: Session,
    empresa_id: int,
    lancamentos: list[LancamentoRazaoNormalizado],
    movimentos: list[MovimentoOperacionalImportado],
) -> tuple[set[tuple[str, str]], list[dict[str, Any]]]:
    rows = session.execute(
        select(
            ReviewItem.id,
            ReviewItem.criticality,
            ReviewItem.status,
            ReviewEvidence.source_type,
            ReviewEvidence.source_id,
        )
        .join(ReviewItem, ReviewEvidence.review_item_id == ReviewItem.id)
        .where(
            ReviewItem.empresa_id == empresa_id,
            ReviewEvidence.source_type.in_(("razao_line", "movimento_operacional")),
        )
        .order_by(ReviewItem.id, ReviewEvidence.source_type, ReviewEvidence.source_id)
    ).all()
    razao_ids = {
        f"{item.lote_id}:{item.linha_original}"
        for item in lancamentos if item.linha_original
    }
    legacy_lotes = {f"{item.lote_id}:" for item in lancamentos if not item.linha_original}
    movement_ids = {str(item.id) for item in movimentos}
    rows = [
        row for row in rows
        if (
            row.source_type == "movimento_operacional" and row.source_id in movement_ids
        ) or (
            row.source_type == "razao_line" and (
                row.source_id in razao_ids
                or any(row.source_id.startswith(prefix) for prefix in legacy_lotes)
            )
        )
    ]
    blocked = {
        (source_type, source_id)
        for _id, criticality, status, source_type, source_id in rows
        if criticality == "critical" and status != "resolved"
    }
    references = [
        {
            "id": item_id,
            "criticality": criticality,
            "status": status,
            "source_type": source_type,
            "source_id": source_id,
        }
        for item_id, criticality, status, source_type, source_id in rows
    ]
    return blocked, references


def _razao_has_critical_review(
    lancamento: LancamentoRazaoNormalizado,
    critical_sources: set[tuple[str, str]],
) -> bool:
    if lancamento.linha_original:
        return ("razao_line", f"{lancamento.lote_id}:{lancamento.linha_original}") in critical_sources
    prefix = f"{lancamento.lote_id}:"
    return any(kind == "razao_line" and source_id.startswith(prefix) for kind, source_id in critical_sources)
