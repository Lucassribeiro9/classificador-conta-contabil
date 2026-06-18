from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, aliased

from core.models import (
    ContaContabil,
    FeedbackClassificacao,
    LancamentoRazaoNormalizado,
)


@dataclass(frozen=True)
class DatasetTreinoContrapartida:
    linhas: list[dict[str, Any]]
    metadata: dict[str, Any]


def build_dataset_treino_contrapartida(
    session: Session,
    *,
    empresa_id: int | None,
) -> DatasetTreinoContrapartida:
    """Monta o contrato inicial do dataset de contrapartida por empresa.

    Esta primeira versao define a fronteira entre lancamentos normalizados e
    consumo futuro pelo ML. Regras adicionais de elegibilidade entram nas
    proximas issues da spec.
    """
    if empresa_id is None:
        raise ValueError("empresa_id e obrigatorio")

    conta_origem = aliased(ContaContabil)
    lancamentos_empresa = session.query(LancamentoRazaoNormalizado).filter(
        LancamentoRazaoNormalizado.empresa_id == empresa_id
    )

    lancamentos_financeiros = (
        lancamentos_empresa
        .join(
            conta_origem,
            conta_origem.codigo == LancamentoRazaoNormalizado.conta_origem,
        )
        .filter(LancamentoRazaoNormalizado.empresa_id == empresa_id)
        .filter(conta_origem.is_financial_origin.is_(True))
    )

    lancamentos = (
        lancamentos_financeiros.order_by(LancamentoRazaoNormalizado.id.asc()).all()
    )

    feedback_por_lancamento = _latest_feedback_by_lancamento(
        session,
        empresa_id=empresa_id,
        lancamento_ids=[lancamento.id for lancamento in lancamentos],
    )
    contas_validas = _valid_target_accounts(
        session,
        [
            _target_for_lancamento(lancamento, feedback_por_lancamento)
            for lancamento in lancamentos
        ],
    )
    linhas = []
    for lancamento in lancamentos:
        target = _target_for_lancamento(lancamento, feedback_por_lancamento)
        if target in contas_validas:
            linhas.append(_to_dataset_row(lancamento, target=target))
    contagem_por_target = _count_targets(linhas)
    total_descartes = lancamentos_empresa.count() - len(linhas)
    treinavel = len(linhas) >= 10 and len(contagem_por_target) >= 2

    return DatasetTreinoContrapartida(
        linhas=linhas,
        metadata={
            "empresa_id": empresa_id,
            "total_linhas": len(linhas),
            "total_descartes": total_descartes,
            "contagem_por_target": contagem_por_target,
            "treinavel": treinavel,
        },
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


def _target_for_lancamento(
    lancamento: LancamentoRazaoNormalizado,
    feedback_por_lancamento: dict[int, int],
) -> int:
    return feedback_por_lancamento.get(
        lancamento.id,
        lancamento.conta_contrapartida,
    )


def _latest_feedback_by_lancamento(
    session: Session,
    *,
    empresa_id: int,
    lancamento_ids: list[int],
) -> dict[int, int]:
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
    latest: dict[int, int] = {}
    for feedback in feedbacks:
        latest[feedback.lancamento_id] = feedback.conta_final
    return latest


def _valid_target_accounts(session: Session, targets: list[int]) -> set[int]:
    if not targets:
        return set()

    return {
        conta.codigo
        for conta in session.query(ContaContabil)
        .filter(ContaContabil.codigo.in_(set(targets)))
        .filter(ContaContabil.tipo == "A")
        .filter(ContaContabil.is_active.is_(True))
        .all()
    }


def _count_targets(linhas: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for linha in linhas:
        target = linha["target_conta_contrapartida"]
        counts[target] = counts.get(target, 0) + 1
    return counts
