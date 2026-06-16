import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, get_current_user, require_company_access
from api.schemas import ImportacaoRazaoResponse
from core.models import Empresa, Usuario
from core.razao_importer import RazaoImportError, import_razao
from core.razao_parser import RazaoParseError


router = APIRouter(prefix="/companies/{company_id}/razao")


@router.post("/import", response_model=ImportacaoRazaoResponse)
def import_company_razao(
    company_id: int,
    file: UploadFile,
    empresa: Empresa = Depends(require_company_access("operacao")),
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ImportacaoRazaoResponse:
    if empresa.id != company_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")

    temp_path = _save_upload_to_temp_xlsx(file)
    try:
        resumo = import_razao(
            db,
            temp_path,
            empresa_id=company_id,
            usuario_id=current_user.id,
            original_filename=file.filename,
        )
        db.commit()
    except (RazaoImportError, RazaoParseError) as exc:
        db.rollback()
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
