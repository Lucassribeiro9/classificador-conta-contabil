from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import get_db
from core import models

router = APIRouter()


@router.patch("/transactions/{transaction_id}/feedback")
def submit_feedback(
    transaction_id: int, feedback: schemas.FeedbackUpdate, db: Session = Depends(get_db)
):
    # Permite a intervenção do usuário para corrigir a conta contábil, alimentando a IA
    db_transacttion = (
        db.query(models.Transacao).filter(models.Transacao.id == transaction_id).first()
    )
    if not db_transacttion:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    db_transacttion.conta_contabil = feedback.conta_contabil
    db.commit()
    db.refresh(db_transacttion)

    print(
        f"Transação {transaction_id} atualizada com conta contábil {feedback.conta_contabil}"
    )

    return db_transacttion
