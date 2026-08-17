from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from core.models import (
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
)


class MovimentoOperacionalSnapshotError(ValueError):
    """Erro de dominio ao montar snapshot operacional exportavel."""


class LoteOperacionalSnapshotNotFound(MovimentoOperacionalSnapshotError):
    """Indica lote inexistente ou fora da empresa solicitada."""


@dataclass(frozen=True)
class MovimentoOperacionalSnapshotItem:
    """Linha exportavel de movimento operacional sem depender de Excel ou HTTP."""

    lote_id: int
    movimento_id: int
    empresa_id: int
    linha_original: int
    layout_version: str
    export_revision: str
    row_version: int
    data: date
    conta_financeira: int
    historico: str
    historico_normalizado: str
    valor_original: Decimal
    valor_absoluto: Decimal
    direcao: str
    tipo_movimento: str | None
    documento: str | None
    observacao: str | None
    contrapartida: int | None
    contrapartida_sugerida: int | None
    confidence_sugerida: float | None
    contrapartida_final: int | None
    status_atual: str
    mensagem_validacao: list[str]
    saldo_observado_original: str | None
    saldo_observado_decimal: Decimal | None
    saldo_calculado_decimal: Decimal | None
    warnings_saldo: list[str]


@dataclass(frozen=True)
class LoteOperacionalSnapshot:
    """Snapshot exportavel do estado atual de um lote operacional."""

    lote_id: int
    empresa_id: int
    layout_version: str
    export_revision: str
    movimentos: list[MovimentoOperacionalSnapshotItem]


def build_lote_operacional_snapshot(
    session: Session,
    *,
    empresa_id: int,
    lote_id: int,
) -> LoteOperacionalSnapshot:
    """Monta snapshot versionado do lote operacional sem arquivo original."""

    lote = (
        session.query(LoteImportacaoMovimentoOperacional)
        .filter(
            LoteImportacaoMovimentoOperacional.id == lote_id,
            LoteImportacaoMovimentoOperacional.empresa_id == empresa_id,
        )
        .first()
    )
    if lote is None:
        raise LoteOperacionalSnapshotNotFound(
            "Lote operacional nao encontrado para a empresa informada."
        )

    export_revision = str(uuid4())
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .filter(
            MovimentoOperacionalImportado.lote_id == lote.id,
            MovimentoOperacionalImportado.empresa_id == empresa_id,
        )
        .order_by(
            MovimentoOperacionalImportado.linha_original.asc(),
            MovimentoOperacionalImportado.id.asc(),
        )
        .all()
    )

    return LoteOperacionalSnapshot(
        lote_id=lote.id,
        empresa_id=lote.empresa_id,
        layout_version=lote.layout_version,
        export_revision=export_revision,
        movimentos=[
            _to_snapshot_item(
                movimento,
                layout_version=lote.layout_version,
                export_revision=export_revision,
            )
            for movimento in movimentos
        ],
    )


def _to_snapshot_item(
    movimento: MovimentoOperacionalImportado,
    *,
    layout_version: str,
    export_revision: str,
) -> MovimentoOperacionalSnapshotItem:
    """Converte movimento persistido para linha de snapshot."""

    return MovimentoOperacionalSnapshotItem(
        lote_id=movimento.lote_id,
        movimento_id=movimento.id,
        empresa_id=movimento.empresa_id,
        linha_original=movimento.linha_original,
        layout_version=layout_version,
        export_revision=export_revision,
        row_version=movimento.row_version,
        data=movimento.data,
        conta_financeira=movimento.conta_financeira,
        historico=movimento.historico,
        historico_normalizado=movimento.historico_normalizado,
        valor_original=movimento.valor_original,
        valor_absoluto=movimento.valor_absoluto,
        direcao=movimento.direcao,
        tipo_movimento=movimento.tipo_movimento,
        documento=movimento.documento,
        observacao=movimento.observacao,
        contrapartida=movimento.contrapartida_informada,
        contrapartida_sugerida=movimento.contrapartida_sugerida,
        confidence_sugerida=movimento.confidence_sugerida,
        contrapartida_final=movimento.contrapartida_final,
        status_atual=movimento.status,
        mensagem_validacao=list(movimento.mensagens_validacao or []),
        saldo_observado_original=None,
        saldo_observado_decimal=None,
        saldo_calculado_decimal=None,
        warnings_saldo=[],
    )
