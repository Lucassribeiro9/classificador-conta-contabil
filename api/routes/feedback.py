import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import (
    DB_DEPENDENCY,
    get_current_user,
    require_company_access,
    verify_api_key,
)
from core.audit import record_audit_event
from core.models import (
    ContaContabil,
    Empresa,
    FeedbackClassificacao,
    LancamentoRazaoNormalizado,
    Transacao,
    Usuario,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/companies/{company_id}/ml/feedback",
    response_model=schemas.FeedbackClassificacaoResponse,
)
def submit_feedback_classificacao(
    company_id: int,
    feedback: schemas.FeedbackClassificacaoCreate,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
    current_user: Usuario = Depends(get_current_user),
):
    lancamento = db.get(LancamentoRazaoNormalizado, feedback.lancamento_id)
    if lancamento is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if lancamento.empresa_id != company_id:
        raise HTTPException(
            status_code=403,
            detail="Lançamento pertence a outra empresa",
        )

    conta_final = (
        db.query(ContaContabil)
        .filter(ContaContabil.codigo == feedback.conta_final)
        .filter(ContaContabil.tipo == "A")
        .filter(ContaContabil.is_active.is_(True))
        .first()
    )
    if conta_final is None:
        raise HTTPException(
            status_code=422,
            detail="Conta final deve ser analítica e ativa",
        )

    feedback_anterior = (
        db.query(FeedbackClassificacao)
        .filter(FeedbackClassificacao.empresa_id == company_id)
        .filter(FeedbackClassificacao.lancamento_id == feedback.lancamento_id)
        .order_by(FeedbackClassificacao.created_at.desc(), FeedbackClassificacao.id.desc())
        .first()
    )

    registro = FeedbackClassificacao(
        empresa_id=company_id,
        lancamento_id=feedback.lancamento_id,
        conta_sugerida=feedback.conta_sugerida,
        conta_final=feedback.conta_final,
        usuario_id=current_user.id,
    )
    db.add(registro)
    db.flush()
    record_audit_event(
        db,
        event_type="feedback.updated" if feedback_anterior else "feedback.created",
        user_id=current_user.id,
        empresa_id=company_id,
        resource_id=str(registro.id),
        metadata={
            "lancamento_id": feedback.lancamento_id,
            "conta_anterior": (
                feedback_anterior.conta_final
                if feedback_anterior
                else feedback.conta_sugerida
            ),
            "conta_corrigida": feedback.conta_final,
        },
    )
    db.commit()
    db.refresh(registro)

    logger.info(
        "Feedback de classificacao registrado",
        extra={
            "feedback_id": registro.id,
            "empresa_id": company_id,
            "lancamento_id": feedback.lancamento_id,
            "usuario_id": current_user.id,
        },
    )

    return registro


@router.patch("/transactions/{transaction_id}/feedback")
def submit_feedback(
    transaction_id: int,
    feedback: schemas.FeedbackUpdate,
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(verify_api_key),
):
    # Permite a intervenção do usuário para corrigir a conta contábil, alimentando a IA
    db_transaction = db.query(Transacao).filter(Transacao.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    if db_transaction.empresa_id != empresa.id:
        raise HTTPException(status_code=403, detail="Transação pertence a outra empresa")
    if not empresa.is_active:
        raise HTTPException(status_code=400, detail="Empresa está desativada")
    db_transaction.conta_contabil = feedback.conta_contabil
    db.commit()
    db.refresh(db_transaction)

    logger.info(
        "Feedback aplicado na transacao",
        extra={
            "transaction_id": transaction_id,
            "conta_contabil": feedback.conta_contabil,
            "empresa_id": empresa.id,
        },
    )

    return db_transaction
