import os
import tempfile
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, get_current_user, require_global_admin
from api.schemas import (
    ContaContabilFinancialOriginUpdate,
    ContaContabilResponse,
    ImportacaoPlanoContasResponse,
)
from core.audit import record_audit_event
from core.models import ContaContabil, Usuario
from core.plano_contas_importer import import_plano_contas
from core.plano_contas_parser import PlanoContasParseError, parse_plano_contas_xlsx


admin_router = APIRouter(prefix="/admin/plano-contas")
catalog_router = APIRouter(prefix="/plano-contas")


@admin_router.post("/import", response_model=ImportacaoPlanoContasResponse)
def import_chart_of_accounts(
    file: UploadFile,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> ImportacaoPlanoContasResponse:
    """Importa o plano de contas do escritorio a partir de um arquivo `.xlsx`.

    A importacao e restrita a usuarios `admin`, reutiliza o parser e o servico
    de persistencia do catalogo, e retorna apenas os contadores do processamento.
    """
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

    temp_path = _save_upload_to_temp_xlsx(file)
    try:
        contas = parse_plano_contas_xlsx(temp_path)
        resumo = import_plano_contas(db, contas)
        record_audit_event(
            db,
            event_type="plan.imported",
            metadata=asdict(resumo),
        )
        db.commit()
    except PlanoContasParseError as exc:
        db.rollback()
        record_audit_event(
            db,
            event_type="plan.import_failed",
            metadata={
                "criadas": 0,
                "atualizadas": 0,
                "ignoradas": 0,
                "invalidas": 0,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        os.unlink(temp_path)

    return ImportacaoPlanoContasResponse(**asdict(resumo))


@admin_router.patch("/{codigo}/financial-origin", response_model=ContaContabilResponse)
def update_chart_account_financial_origin(
    codigo: int,
    update: ContaContabilFinancialOriginUpdate,
    admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> ContaContabil:
    conta = _get_chart_account_by_codigo_or_404(db, codigo)
    old_value = conta.is_financial_origin
    conta.is_financial_origin = update.is_financial_origin
    record_audit_event(
        db,
        event_type="account.updated",
        user_id=admin.id,
        resource_id=str(conta.codigo),
        metadata={
            "field": "is_financial_origin",
            "old_value": old_value,
            "new_value": conta.is_financial_origin,
        },
    )
    db.commit()
    db.refresh(conta)
    return conta


@admin_router.patch("/{codigo}/deactivate", response_model=ContaContabilResponse)
def deactivate_chart_account(
    codigo: int,
    admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> ContaContabil:
    conta = _get_chart_account_by_codigo_or_404(db, codigo)
    old_value = conta.is_active
    conta.is_active = False
    record_audit_event(
        db,
        event_type="account.deactivated",
        user_id=admin.id,
        resource_id=str(conta.codigo),
        metadata={
            "field": "is_active",
            "old_value": old_value,
            "new_value": conta.is_active,
        },
    )
    db.commit()
    db.refresh(conta)
    return conta


def _save_upload_to_temp_xlsx(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(file.file.read())
        return temp_file.name


def _get_chart_account_by_codigo_or_404(db: Session, codigo: int) -> ContaContabil:
    conta = db.query(ContaContabil).filter(ContaContabil.codigo == codigo).first()
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta contábil não encontrada")
    return conta


@catalog_router.get("", response_model=list[ContaContabilResponse])
def list_chart_accounts(
    codigo: int | None = Query(None, description="Filtra pelo codigo da conta"),
    nome: str | None = Query(None, description="Filtra por trecho do nome"),
    tipo: str | None = Query(None, description="Filtra por tipo A ou S"),
    is_active: bool | None = Query(None, description="Filtra por status ativo"),
    is_financial_origin: bool | None = Query(
        None,
        description="Filtra contas candidatas a origem financeira",
    ),
    _current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> list[ContaContabil]:
    """Lista contas do catalogo unico para usuarios internos autenticados."""
    query = db.query(ContaContabil)

    if codigo is not None:
        query = query.filter(ContaContabil.codigo == codigo)
    if nome is not None:
        query = query.filter(ContaContabil.nome.ilike(f"%{nome}%"))
    if tipo is not None:
        query = query.filter(ContaContabil.tipo == tipo.upper())
    if is_active is not None:
        query = query.filter(ContaContabil.is_active == is_active)
    if is_financial_origin is not None:
        query = query.filter(
            ContaContabil.is_financial_origin == is_financial_origin
        )

    return query.order_by(ContaContabil.codigo.asc()).all()


@catalog_router.get("/id/{account_id}", response_model=ContaContabilResponse)
def get_chart_account_by_id(
    account_id: int,
    _current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ContaContabil:
    """Retorna dados oficiais de uma conta pelo identificador interno."""
    conta = db.get(ContaContabil, account_id)
    if conta is None:
        raise HTTPException(status_code=404, detail="Conta contábil não encontrada")
    return conta


@catalog_router.get("/{codigo}", response_model=ContaContabilResponse)
def get_chart_account_by_codigo(
    codigo: int,
    _current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ContaContabil:
    """Retorna dados oficiais de uma conta pelo codigo contabil."""
    return _get_chart_account_by_codigo_or_404(db, codigo)
