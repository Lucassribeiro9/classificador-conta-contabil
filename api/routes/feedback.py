from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import get_db, verify_api_key
from core.models import Empresa, Transacao

router = APIRouter()


@router.patch("/transactions/{transaction_id}/feedback")
def submit_feedback(
    transaction_id: int, feedback: schemas.FeedbackUpdate, db: Session = Depends(get_db), empresa: Empresa = Depends(verify_api_key)
):
    # Permite a intervenção do usuário para corrigir a conta contábil, alimentando a IA
    db_transaction = (
        db.query(Transacao).filter(Transacao.id == transaction_id).first()
    )
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    db_transaction.conta_contabil = feedback.conta_contabil
    db.commit()
    db.refresh(db_transaction)

    print(
        f"Transação {transaction_id} atualizada com conta contábil {feedback.conta_contabil}"
    )

    return db_transaction
