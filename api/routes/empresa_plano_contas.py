"""Leitura de contas contabeis no contexto autorizado de uma empresa."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_company_access
from api.schemas import ContaContabilContextualResponse
from core.conta_contabil_empresa import listar_contas_contabeis, resolver_conta_contabil
from core.models import Empresa


router = APIRouter(prefix="/empresas/{company_id}/plano-contas")


@router.get("", response_model=list[ContaContabilContextualResponse])
def list_company_chart_accounts(
    company_id: int,
    codigo: int | None = Query(None),
    nome: str | None = Query(None),
    tipo: str | None = Query(None),
    is_active: bool | None = Query(None),
    is_financial_origin: bool | None = Query(None),
    _empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> list[ContaContabilContextualResponse]:
    contas = listar_contas_contabeis(
        db,
        empresa_id=company_id,
        codigo=codigo,
        nome=nome,
        tipo=tipo,
        is_active=is_active,
        is_financial_origin=is_financial_origin,
    )
    return [ContaContabilContextualResponse.model_validate(conta) for conta in contas]


@router.get("/{codigo}", response_model=ContaContabilContextualResponse)
def get_company_chart_account(
    company_id: int,
    codigo: int,
    _empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> ContaContabilContextualResponse:
    conta = resolver_conta_contabil(db, empresa_id=company_id, codigo=codigo)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta contábil não encontrada")
    return ContaContabilContextualResponse.model_validate(conta)
