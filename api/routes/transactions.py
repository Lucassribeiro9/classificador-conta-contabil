from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import DB_DEPENDENCY, verify_company, require_admin_token
from core.models import Empresa, Transacao

# Instanciando o router
router = APIRouter()
_DUPLICATE_DETAIL = (
    "Transação duplicada para os mesmos dados de empresa, data, histórico, valor, conta e banco"
)


def _transaction_signature(transaction_data: dict) -> tuple:
    return (
        transaction_data["empresa_id"],
        transaction_data["data"],
        transaction_data["historico"],
        transaction_data["valor"],
        transaction_data["conta_contabil"],
        transaction_data["cod_banco"],
    )


def _duplicate_filter(company_id: int, transaction_data: dict):
    conta_filter = (
        Transacao.conta_contabil.is_(None)
        if transaction_data["conta_contabil"] is None
        else Transacao.conta_contabil == transaction_data["conta_contabil"]
    )
    banco_filter = (
        Transacao.cod_banco.is_(None)
        if transaction_data["cod_banco"] is None
        else Transacao.cod_banco == transaction_data["cod_banco"]
    )
    return and_(
        Transacao.empresa_id == company_id,
        Transacao.data == transaction_data["data"],
        Transacao.historico == transaction_data["historico"],
        Transacao.valor == transaction_data["valor"],
        conta_filter,
        banco_filter,
    )


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
    """Cria transações em lote para uma empresa específica.

    A empresa é validada por `verify_company`, garantindo:
    - escopo correto por `company_id`;
    - empresa ativa e API key compatível com o contexto da requisição.
    """

    data_transactions = [transaction.model_dump() for transaction in transactions_in]
    for transaction in data_transactions:
        transaction["empresa_id"] = company_id
    seen_signatures = set()
    for transaction in data_transactions:
        signature = _transaction_signature(transaction)
        if signature in seen_signatures:
            raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL)
        seen_signatures.add(signature)

    for transaction in data_transactions:
        duplicate_exists = (
            db.query(Transacao)
            .filter(_duplicate_filter(company_id=company_id, transaction_data=transaction))
            .first()
            is not None
        )
        if duplicate_exists:
            raise HTTPException(status_code=409, detail=_DUPLICATE_DETAIL)

    new_transactions = [Transacao(**transaction) for transaction in data_transactions]
    db.add_all(new_transactions)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=_DUPLICATE_DETAIL,
        )
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
    """Lista transações da empresa com paginação simples.

    Parâmetros:
    - `skip`: deslocamento inicial da lista;
    - `limit`: quantidade máxima retornada.
    """

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
    """Retorna transações marcadas para revisão manual.

    Critério:
    - `needs_review=True`.

    Ordenação:
    - confiança crescente (`confidence` menor primeiro), priorizando
      itens em que o modelo está menos confiante.
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

# DELETE - Deletar transação por ID
@router.delete("/companies/{company_id}/transactions/{transaction_id}", status_code=204)
def delete_transaction(
    company_id: int,
    transaction_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Remove uma transação específica por ID.

    Retorna `404` se a transação não existir ou não pertencer à empresa.
    Em sucesso, retorna `204 No Content`.
    """
    transaction = (
        db.query(Transacao)
        .filter(Transacao.id == transaction_id, Transacao.empresa_id == company_id)
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    db.delete(transaction)
    db.commit()


# DELETE - Deletar transações em lote de uma empresa (possível apenas para o root).
@router.delete(
    "/companies/{company_id}/transactions", response_model=List[schemas.Transacao]
)
def delete_transactions_batch(
    company_id: int,
    _admin=Depends(require_admin_token),
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Remove em lote as transações de uma empresa.

    Possível apenas para o root. Caso a empresa não exista, retorna `404`.
    Em sucesso, retorna `200 OK` com a lista de transações removidas.
    """
    company = db.query(Empresa).filter(Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    transactions = (
        db.query(Transacao).filter(Transacao.empresa_id == company_id).all()
    )
    deleted_transactions = [schemas.Transacao.model_validate(transaction) for transaction in transactions]
    for transaction in transactions:
        db.delete(transaction)
    db.commit()
    return deleted_transactions
