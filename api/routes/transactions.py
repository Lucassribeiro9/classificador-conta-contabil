from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import get_db
from core import models

# Instanciando o router 
router = APIRouter()


# POST - Criar/Adicionar transações em lote
@router.post(
    "/companies/{company_id}/transactions", response_model=List[schemas.Transacao]
)
def create_transactions_batch(
    company_id: int,
    transactions_in: List[schemas.TransacaoCreate],
    db: Session = Depends(get_db),
):
    """Criando transações em lote"""
    empresa = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    data_transactions = [transaction.model_dump() for transaction in transactions_in]
    for transaction in data_transactions:
        transaction["empresa_id"] = company_id
    new_transactions = [
        models.Transacao(**transaction) for transaction in data_transactions
    ]
    db.add_all(new_transactions)
    db.commit()
    for transaction in new_transactions:
        db.refresh(transaction)
    return new_transactions


# GET - Listar transações de uma empresa
@router.get(
    "/companies/{company_id}/transactions", response_model=List[schemas.Transacao]
)
def list_transactions(company_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """Listando transações de uma empresa"""
    empresa = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    transactions = (
        db.query(models.Transacao)
        .filter(models.Transacao.empresa_id == company_id)
        .limit(limit)
        .all()
    )
    return transactions
