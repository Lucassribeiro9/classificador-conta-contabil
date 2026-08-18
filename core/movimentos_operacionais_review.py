from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import (
    ContaContabil,
    EmpresaContaContabil,
    MovimentoOperacionalImportado,
)


STATUS_REVISAVEIS = {"pre_classificado", "sugerido", "revisao"}
ACTIONS_WITH_FINAL_ACCOUNT = {"approve", "correct"}


class MovimentoReviewError(Exception):
    pass


def review_movimento_operacional(
    db: Session,
    movimento_id: int,
    empresa_id: int,
    usuario_id: int,
    action: str,
    conta_final: int | None = None,
) -> MovimentoOperacionalImportado:
    """Revisa um movimento operacional individual com regra reutilizavel."""
    movimento = _get_revisable_movimento(db, movimento_id, empresa_id)

    if action == "reject":
        _reject_movimento(db, movimento, empresa_id=empresa_id, usuario_id=usuario_id)
        return movimento

    if action in ACTIONS_WITH_FINAL_ACCOUNT:
        conta_codigo = _require_conta_final(conta_final)
        _ensure_empresa_conta_link(
            db,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            movimento_id=movimento.id,
            conta_codigo=conta_codigo,
        )
        _apply_final_account_review(
            db,
            movimento,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            action=action,
            conta_final=conta_codigo,
        )
        return movimento

    raise MovimentoReviewError(f"Ação {action} desconhecida")


def _get_revisable_movimento(
    db: Session,
    movimento_id: int,
    empresa_id: int,
) -> MovimentoOperacionalImportado:
    """Carrega movimento da empresa e valida se ainda pode ser revisado."""
    movimento = db.get(MovimentoOperacionalImportado, movimento_id)
    if not movimento or movimento.empresa_id != empresa_id:
        raise MovimentoReviewError("Movimento não encontrado")
    if movimento.status not in STATUS_REVISAVEIS:
        raise MovimentoReviewError("Status não permite revisão")
    return movimento


def _reject_movimento(
    db: Session,
    movimento: MovimentoOperacionalImportado,
    *,
    empresa_id: int,
    usuario_id: int,
) -> None:
    """Rejeita movimento e remove qualquer par final previamente preenchido."""
    movimento.status = "rejeitado"
    movimento.contrapartida_final = None
    movimento.conta_debito = None
    movimento.conta_credito = None
    movimento.elegivel_treino = False
    record_audit_event(
        db,
        event_type="operational_movements.rejected",
        user_id=usuario_id,
        empresa_id=empresa_id,
        resource_id=str(movimento.id),
        metadata={"action": "reject"},
    )


def _require_conta_final(conta_final: int | None) -> int:
    """Garante conta final informada para aprovacao ou correcao."""
    if not conta_final:
        raise MovimentoReviewError("conta_final é obrigatória para aprovação/correção")
    return conta_final


def _ensure_empresa_conta_link(
    db: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    movimento_id: int,
    conta_codigo: int,
) -> None:
    """Valida conta classificavel e cria vinculo empresa-conta quando necessario."""
    conta = db.scalars(
        select(ContaContabil).where(ContaContabil.codigo == conta_codigo)
    ).first()
    if not conta or not conta.is_classificavel:
        raise MovimentoReviewError("Conta final inválida ou inativa")

    vinculo = db.scalars(
        select(EmpresaContaContabil).where(
            EmpresaContaContabil.empresa_id == empresa_id,
            EmpresaContaContabil.conta_codigo == conta_codigo,
        )
    ).first()
    if vinculo:
        return

    db.add(
        EmpresaContaContabil(
            empresa_id=empresa_id,
            conta_codigo=conta_codigo,
            ultima_utilizacao=date.today(),
        )
    )
    db.flush()
    record_audit_event(
        db,
        event_type="empresa_conta.created_by_review",
        user_id=usuario_id,
        empresa_id=empresa_id,
        metadata={"conta_codigo": conta_codigo, "movimento_id": movimento_id},
    )


def _apply_final_account_review(
    db: Session,
    movimento: MovimentoOperacionalImportado,
    *,
    empresa_id: int,
    usuario_id: int,
    action: str,
    conta_final: int,
) -> None:
    """Aplica aprovacao ou correcao sem alterar entrada, sugestao ou confianca."""
    movimento.contrapartida_final = conta_final
    movimento.status = "aprovado" if action == "approve" else "corrigido"
    movimento.elegivel_treino = True

    if movimento.direcao == "debito":
        movimento.conta_debito = movimento.conta_financeira
        movimento.conta_credito = conta_final
    else:
        movimento.conta_debito = conta_final
        movimento.conta_credito = movimento.conta_financeira

    record_audit_event(
        db,
        event_type=f"operational_movements.{movimento.status}",
        user_id=usuario_id,
        empresa_id=empresa_id,
        resource_id=str(movimento.id),
        metadata={"conta_final": conta_final},
    )
