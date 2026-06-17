from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, aliased

from core.models import ContaContabil, LancamentoRazaoNormalizado


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
    conta_target = aliased(ContaContabil)

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
        lancamentos_financeiros
        .join(
            conta_target,
            conta_target.codigo == LancamentoRazaoNormalizado.conta_contrapartida,
        )
        .filter(conta_target.tipo == "A")
        .filter(conta_target.is_active.is_(True))
        .order_by(LancamentoRazaoNormalizado.id.asc())
        .all()
    )

    linhas = [_to_dataset_row(lancamento) for lancamento in lancamentos]
    contagem_por_target = _count_targets(linhas)
    total_descartes = lancamentos_empresa.count() - len(linhas)

    return DatasetTreinoContrapartida(
        linhas=linhas,
        metadata={
            "empresa_id": empresa_id,
            "total_linhas": len(linhas),
            "total_descartes": total_descartes,
            "contagem_por_target": contagem_por_target,
            "treinavel": len(linhas) >= 1,
        },
    )


def _to_dataset_row(lancamento: LancamentoRazaoNormalizado) -> dict[str, Any]:
    feature_tokens = [
        lancamento.historico_normalizado.strip(),
        f"origem_{lancamento.conta_origem}",
        f"direcao_{lancamento.direcao}",
    ]

    return {
        "features": " ".join(token for token in feature_tokens if token),
        "target_conta_contrapartida": lancamento.conta_contrapartida,
    }


def _count_targets(linhas: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for linha in linhas:
        target = linha["target_conta_contrapartida"]
        counts[target] = counts.get(target, 0) + 1
    return counts
