from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date

from core.models import (
    MovimentoOperacionalImportado,
    ContaContabil,
    EmpresaContaContabil,
)
from core.audit import record_audit_event

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
    """
    Revisa um movimento operacional (aprovar, corrigir, rejeitar).
    """
    mov = db.get(MovimentoOperacionalImportado, movimento_id)
    if not mov or mov.empresa_id != empresa_id:
        raise MovimentoReviewError("Movimento não encontrado")

    if action == "reject":
        mov.status = "rejeitado"
        mov.elegivel_treino = False
        record_audit_event(
            db,
            event_type="operational_movements.rejected",
            user_id=usuario_id,
            empresa_id=empresa_id,
            resource_id=str(mov.id),
            metadata={"action": "reject"}
        )
        return mov

    if action in ("approve", "correct"):
        if not conta_final:
            raise MovimentoReviewError("conta_final é obrigatória para aprovação/correção")
            
        conta = db.scalars(
            select(ContaContabil).where(ContaContabil.codigo == conta_final)
        ).first()
        
        if not conta or not conta.is_classificavel:
            raise MovimentoReviewError("Conta final inválida ou inativa")

        # Criar vínculo empresa_conta_contabil se não existir
        vinculo = db.scalars(
            select(EmpresaContaContabil).where(
                EmpresaContaContabil.empresa_id == empresa_id,
                EmpresaContaContabil.conta_codigo == conta_final
            )
        ).first()
        
        if not vinculo:
            vinculo = EmpresaContaContabil(
                empresa_id=empresa_id,
                conta_codigo=conta_final,
                ultima_utilizacao=date.today()
            )
            db.add(vinculo)
            db.flush()
            record_audit_event(
                db,
                event_type="empresa_conta.created_by_review",
                user_id=usuario_id,
                empresa_id=empresa_id,
                metadata={"conta_codigo": conta_final, "movimento_id": mov.id}
            )

        mov.contrapartida_final = conta_final
        mov.status = "aprovado" if action == "approve" else "corrigido"
        mov.elegivel_treino = True
        
        # Par débito/crédito
        if mov.direcao == "debito":
            mov.conta_debito = mov.conta_financeira
            mov.conta_credito = conta_final
        else:
            mov.conta_debito = conta_final
            mov.conta_credito = mov.conta_financeira

        record_audit_event(
            db,
            event_type=f"operational_movements.{mov.status}",
            user_id=usuario_id,
            empresa_id=empresa_id,
            resource_id=str(mov.id),
            metadata={"conta_final": conta_final}
        )
        return mov

    raise MovimentoReviewError(f"Ação {action} desconhecida")
