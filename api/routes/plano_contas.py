import os
import tempfile
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_global_admin
from api.schemas import ImportacaoPlanoContasResponse
from core.models import Usuario
from core.plano_contas_importer import import_plano_contas
from core.plano_contas_parser import PlanoContasParseError, parse_plano_contas_xlsx


router = APIRouter(prefix="/admin/plano-contas")


@router.post("/import", response_model=ImportacaoPlanoContasResponse)
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
        db.commit()
    except PlanoContasParseError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        os.unlink(temp_path)

    return ImportacaoPlanoContasResponse(**asdict(resumo))


def _save_upload_to_temp_xlsx(file: UploadFile) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        temp_file.write(file.file.read())
        return temp_file.name
