from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import DB_DEPENDENCY, verify_company
from core.models import Empresa, Transacao

# Instanciando o router
router = APIRouter()


# POST - Criar/Adicionar transações em lote
@router.post(
    "/companies/{company_id}/transactions", response_model=List[schemas.Transacao]
)
def create_transactions_batch(
    company_id: int,
    transactions_in: List[schemas.TransacaoCreate],
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Criando transações em lote"""

    data_transactions = [transaction.model_dump() for transaction in transactions_in]
    for transaction in data_transactions:
        transaction["empresa_id"] = company_id
    new_transactions = [Transacao(**transaction) for transaction in data_transactions]
    db.add_all(new_transactions)
    db.commit()
    for transaction in new_transactions:
        db.refresh(transaction)
    return new_transactions


# GET - Listar transações de uma empresa
@router.get(
    "/companies/{company_id}/transactions", response_model=List[schemas.Transacao]
)
def list_transactions(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Listando transações de uma empresa"""

    transactions = (
        db.query(Transacao)
        .filter(Transacao.empresa_id == company_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return transactions


# GET - Listar transações que precisam de revisão
@router.get(
    "/companies/{company_id}/transactions/needs_review",
    response_model=List[schemas.Transacao],
)
def list_transactions_for_review(
    company_id: int,
    limit: int = 100,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Retorna transações que precisam de revisão manual (needs_review=True).
    As transações são ordenadas por confidence (menor primeiro) para priorizar
    as que o modelo tem menos certeza.
    """

    transactions = (
        db.query(Transacao)
        .filter(
            Transacao.empresa_id == company_id,
            Transacao.needs_review == True,
        )
        .order_by(Transacao.confidence.asc())  # Menor confiança primeiro
        .limit(limit)
        .all()
    )
    return transactions
