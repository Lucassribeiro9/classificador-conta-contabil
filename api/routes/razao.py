import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, get_current_user, require_global_admin
from api.schemas import ImportacaoRazaoResponse
from core.audit import record_audit_event
from core.models import Empresa, LoteImportacaoRazao, Usuario
from core.razao_importer import RazaoImportError, import_razao
from core.razao_parser import RazaoParseError


router = APIRouter(prefix="/companies/{company_id}/razao")
admin_router = APIRouter(prefix="/admin/razao")


@router.post("/import", response_model=ImportacaoRazaoResponse)
def import_company_razao(
    company_id: int,
    file: UploadFile,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ImportacaoRazaoResponse:
    temp_path = _save_upload_to_temp_xlsx(file)
    file_hash = _file_hash(temp_path)
    try:
        empresa = db.get(Empresa, company_id)
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")
        denial_detail = _razao_permission_denial_detail(current_user, company_id)
        if denial_detail is not None:
            record_audit_event(
                db,
                event_type="ledger.import_denied",
                user_id=current_user.id,
                empresa_id=company_id,
                metadata={
                    "file_hash": file_hash,
                    "reason": (
                        "insufficient_permission"
                        if denial_detail == "Permissão insuficiente"
                        else "access_denied"
                    ),
                },
            )
            db.commit()
            raise HTTPException(status_code=403, detail=denial_detail)

        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            record_audit_event(
                db,
                event_type="ledger.import_failed",
                user_id=current_user.id,
                empresa_id=company_id,
                metadata={
                    "file_hash": file_hash,
                    "total_linhas": 0,
                    "total_importadas": 0,
                    "total_invalidas": 0,
                    "warnings": [],
                    "error_type": "InvalidFileType",
                    "error": "Arquivo deve ser .xlsx",
                    "reason": "invalid_file_type",
                },
            )
            db.commit()
            raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

        resumo = import_razao(
            db,
            temp_path,
            empresa_id=company_id,
            usuario_id=current_user.id,
            original_filename=file.filename,
        )
        record_audit_event(
            db,
            event_type="ledger.imported",
            user_id=current_user.id,
            empresa_id=company_id,
            resource_id=str(resumo.lote_id),
            metadata={
                "file_hash": file_hash,
                "total_linhas": resumo.total_linhas,
                "total_importadas": resumo.total_importadas,
                "total_invalidas": resumo.total_invalidas,
                "warnings": resumo.warnings,
            },
        )
        db.commit()
    except (RazaoImportError, RazaoParseError) as exc:
        db.rollback()
        record_audit_event(
            db,
            event_type="ledger.import_failed",
            user_id=current_user.id,
            empresa_id=company_id,
            metadata={
                "file_hash": file_hash,
                "total_linhas": 0,
                "total_importadas": 0,
                "total_invalidas": 0,
                "warnings": [],
                "error_type": type(exc).__name__,
                "error": str(exc),
                "reason": _failure_reason(exc),
            },
        )
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        os.unlink(temp_path)

    return ImportacaoRazaoResponse(**resumo.__dict__)


def _save_upload_to_temp_xlsx(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(file.file.read())
        return temp_file.name


def _file_hash(path: str) -> str:
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _razao_permission_denial_detail(user: Usuario, company_id: int) -> str | None:
    if user.papel == "admin":
        return None

    permission_link = next(
        (
            permission
            for permission in user.permissoes_empresas
            if permission.empresa_id == company_id
        ),
        None,
    )
    if permission_link is None:
        return "Acesso negado"
    if permission_link.permissao not in {"operacao", "admin_empresa"}:
        return "Permissão insuficiente"
    return None


def _failure_reason(exc: Exception) -> str:
    if isinstance(exc, RazaoImportError) and "Arquivo ja importado" in str(exc):
        return "duplicate_file_hash"
    if (
        isinstance(exc, RazaoImportError)
        and "CNPJ do razao nao corresponde" in str(exc)
    ):
        return "company_mismatch"
    return "invalid_file"


@admin_router.delete("/lotes/{lote_id}", status_code=204)
def delete_ledger_import_batch(
    lote_id: int,
    admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> None:
    lote = db.get(LoteImportacaoRazao, lote_id)
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote de razão não encontrado")

    metadata = {
        "lote_id": lote.id,
        "original_filename": lote.original_filename,
        "file_hash": lote.file_hash,
        "status": lote.status,
        "created_at": lote.created_at.isoformat(),
    }
    record_audit_event(
        db,
        event_type="ledger.deleted",
        user_id=admin.id,
        empresa_id=lote.empresa_id,
        resource_id=str(lote.id),
        metadata=metadata,
    )
    db.delete(lote)
    db.commit()
    return None
