"""Leitura de contas contabeis no contexto autorizado de uma empresa."""

from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, get_current_user, require_company_access
from api.schemas import ContaContabilContextualResponse
from core.conta_contabil_empresa import listar_contas_contabeis, resolver_conta_contabil
from core.models import (
    Empresa,
    PlanoContasConflictDecision,
    PlanoContasImportEvent,
    PlanoContasSnapshot,
    ReviewEvidence,
    Usuario,
)
from core.plano_contas_parser import PlanoContasParseError, parse_plano_contas_xlsx
from core.plano_contas_snapshots import (
    SnapshotConflict,
    importar_snapshot,
    resolver_conflito,
    selecionar_snapshot,
)
from core.review_items import ReviewItemConflict


router = APIRouter(prefix="/empresas/{company_id}/plano-contas")


class SnapshotResolutionRequest(BaseModel):
    snapshot_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)


@router.get("/snapshots/conflicts/{item_id}/decision")
def get_snapshot_conflict_decision(
    company_id: int,
    item_id: int,
    _empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> dict:
    decision = (
        db.query(PlanoContasConflictDecision)
        .filter(
            PlanoContasConflictDecision.empresa_id == company_id,
            PlanoContasConflictDecision.review_item_id == item_id,
        )
        .first()
    )
    if decision is None:
        raise HTTPException(status_code=404, detail="Decisão não encontrada")
    evidences = (
        db.query(ReviewEvidence)
        .filter(
            ReviewEvidence.review_item_id == item_id,
            ReviewEvidence.source_type == "snapshot",
        )
        .all()
    )
    return {
        "id": decision.id,
        "empresa_id": company_id,
        "review_item_id": item_id,
        "vigencia": decision.vigencia.isoformat(),
        "snapshot_ids": sorted(int(evidence.source_id) for evidence in evidences),
        "selected_snapshot_id": decision.selected_snapshot_id,
        "user_id": decision.user_id,
        "reason": decision.reason,
        "decided_at": decision.decided_at.isoformat(),
    }


@router.post("/snapshots/import")
def import_company_snapshot(
    company_id: int,
    file: UploadFile = File(...),
    origem: str = Form(...),
    vigencia: date | None = Form(None),
    _empresa: Empresa = Depends(require_company_access("operacao")),
    db: Session = DB_DEPENDENCY,
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx")
    with NamedTemporaryFile(suffix=".xlsx", delete=False) as target:
        temp_path = Path(target.name)
        while chunk := file.file.read(1024 * 1024):
            target.write(chunk)
    try:
        contas = parse_plano_contas_xlsx(temp_path)
        result = importar_snapshot(
            db, empresa_id=company_id, contas=contas, vigencia=vigencia, origem=origem
        )
        db.commit()
        return {
            "snapshot_id": result.snapshot.id,
            "import_event_id": result.evento.id,
            "content_hash": result.snapshot.content_hash,
            "vigencia": result.evento.vigencia.isoformat(),
            "vigencia_inferida": result.evento.vigencia_inferida,
            "review_item_id": result.review_item_id,
        }
    except (PlanoContasParseError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/snapshots/at/{competencia}")
def get_snapshot_at(
    company_id: int,
    competencia: date,
    _empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> dict:
    try:
        snapshot = selecionar_snapshot(
            db, empresa_id=company_id, competencia=competencia
        )
    except SnapshotConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")
    return {
        "id": snapshot.id,
        "empresa_id": snapshot.empresa_id,
        "content_hash": snapshot.content_hash,
        "content": snapshot.content,
    }


@router.get("/snapshots/{snapshot_id}")
def get_company_snapshot(
    company_id: int,
    snapshot_id: int,
    _empresa: Empresa = Depends(require_company_access("leitura")),
    db: Session = DB_DEPENDENCY,
) -> dict:
    snapshot = (
        db.query(PlanoContasSnapshot)
        .filter(
            PlanoContasSnapshot.id == snapshot_id,
            PlanoContasSnapshot.empresa_id == company_id,
        )
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot não encontrado")
    events = (
        db.query(PlanoContasImportEvent)
        .filter(
            PlanoContasImportEvent.empresa_id == company_id,
            PlanoContasImportEvent.snapshot_id == snapshot_id,
        )
        .order_by(PlanoContasImportEvent.id)
        .all()
    )
    return {
        "id": snapshot.id,
        "empresa_id": snapshot.empresa_id,
        "content_hash": snapshot.content_hash,
        "content": snapshot.content,
        "imports": [
            {
                "id": event.id,
                "origem": event.origem,
                "vigencia": event.vigencia.isoformat(),
                "vigencia_inferida": event.vigencia_inferida,
                "imported_at": event.imported_at.isoformat(),
            }
            for event in events
        ],
    }


@router.post("/snapshots/conflicts/{item_id}/resolve")
def resolve_snapshot_conflict(
    company_id: int,
    item_id: int,
    request: SnapshotResolutionRequest,
    _empresa: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> dict:
    try:
        decision = resolver_conflito(
            db,
            empresa_id=company_id,
            item_id=item_id,
            snapshot_id=request.snapshot_id,
            user_id=user.id,
            reason=request.reason,
        )
        db.commit()
        return {
            "decision_id": decision.id,
            "selected_snapshot_id": decision.selected_snapshot_id,
            "review_item_id": item_id,
        }
    except ReviewItemConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
