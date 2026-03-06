import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import DB_DEPENDENCY, verify_api_key
from core.models import Empresa, Transacao

router = APIRouter()
logger = logging.getLogger(__name__)


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
