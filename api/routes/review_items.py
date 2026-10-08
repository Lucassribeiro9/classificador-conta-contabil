from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, get_current_user, require_company_access
from api.schemas import (
    ReviewAssigneeListResponse,
    ReviewAssigneeResponse,
    ReviewItemListResponse,
    ReviewItemReasonRequest,
    ReviewItemReassignRequest,
    ReviewItemResponse,
    RazaoAliasConfirmationRequest,
)
from core.models import Empresa, ReviewItem, Usuario, UsuarioEmpresaPermissao
from core.review_items import (
    ReviewItemConflict,
    ReviewItemNotFound,
    claim_review_item,
    dismiss_review_item,
    release_review_item,
    reassign_review_item,
    reopen_review_item,
    resolve_review_item,
)
from core.razao_aliases import confirmar_alias_razao
from core.plano_contas_snapshots import SnapshotConflict, selecionar_snapshot


router = APIRouter(prefix="/companies/{company_id}/review-items")


def _response(item: ReviewItem, user: Usuario) -> ReviewItemResponse:
    levels = {"leitura": 1, "operacao": 2, "admin_empresa": 3}
    rank = (
        3
        if user.papel == "admin"
        else max(
            (
                levels.get(permission.permissao, 0)
                for permission in user.permissoes_empresas
                if permission.empresa_id == item.empresa_id
            ),
            default=0,
        )
    )
    actions: list[str] = []
    if rank >= 2 and item.status == "pending":
        actions.append("claim")
    if rank >= 2 and item.status == "in_review" and item.assignee_id == user.id:
        actions.extend(("release", "resolve", "dismiss"))
        if item.source_type == "razao_account_unknown":
            actions.append("confirm_razao_alias")
    if rank >= 3 and item.status == "in_review":
        actions.append("reassign")
    if rank >= 3 and item.status in {"resolved", "dismissed"}:
        actions.append("reopen")
    if item.source_type == "snapshot_conflict":
        actions = [action for action in actions if action not in {"resolve", "dismiss", "reopen"}]
    if item.source_type == "razao_account_unknown":
        actions = [action for action in actions if action != "resolve"]
    data = {
        name: getattr(item, name)
        for name in ReviewItemResponse.model_fields
        if name not in {"available_actions", "assignee_name"}
    }
    data["available_actions"] = actions
    data["assignee_name"] = item.assignee.nome if item.assignee else None
    return ReviewItemResponse.model_validate(data)


def _transition_response(
    operation, *, db: Session, user: Usuario, **kwargs
) -> ReviewItemResponse:
    try:
        item = operation(db, **kwargs)
        db.commit()
        db.refresh(item)
        return _response(item, user)
    except ReviewItemNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Pendência não encontrada") from exc
    except ReviewItemConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=ReviewItemListResponse)
def list_review_items(
    company_id: int,
    status: Literal["open", "pending", "in_review", "resolved", "dismissed"] = "open",
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    _company: Empresa = Depends(require_company_access("leitura")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemListResponse:
    query = db.query(ReviewItem).filter(ReviewItem.empresa_id == company_id)
    if status == "open":
        query = query.filter(ReviewItem.status.in_(("pending", "in_review")))
    else:
        query = query.filter(ReviewItem.status == status)

    total = query.count()
    items = (
        query.order_by(
            case(
                (ReviewItem.criticality == "critical", 4),
                (ReviewItem.criticality == "high", 3),
                (ReviewItem.criticality == "medium", 2),
                (ReviewItem.criticality == "low", 1),
                else_=0,
            ).desc(),
            ReviewItem.source_type.asc(),
            ReviewItem.created_at.asc(),
            ReviewItem.id.asc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return ReviewItemListResponse(
        items=[_response(item, user) for item in items],
        total=total,
        page=page,
        limit=limit,
        has_next=page * limit < total,
    )


@router.get("/assignees", response_model=ReviewAssigneeListResponse)
def list_review_assignees(
    company_id: int,
    _company: Empresa = Depends(require_company_access("admin_empresa")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewAssigneeListResponse:
    query = db.query(Usuario).filter(Usuario.is_active.is_(True))
    if user.papel != "admin":
        query = query.filter(
            or_(
                Usuario.papel == "admin",
                Usuario.permissoes_empresas.any(
                    and_(
                        UsuarioEmpresaPermissao.empresa_id == company_id,
                        UsuarioEmpresaPermissao.permissao.in_(
                            ("operacao", "admin_empresa")
                        ),
                    )
                ),
            )
        )
    return ReviewAssigneeListResponse(
        items=[
            ReviewAssigneeResponse(id=assignee.id, nome=assignee.nome)
            for assignee in query.order_by(Usuario.nome, Usuario.id).all()
        ]
    )


@router.get("/{item_id}", response_model=ReviewItemResponse)
def get_review_item(
    company_id: int,
    item_id: int,
    _company: Empresa = Depends(require_company_access("leitura")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    item = (
        db.query(ReviewItem)
        .filter(ReviewItem.id == item_id, ReviewItem.empresa_id == company_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    return _response(item, user)


@router.post("/{item_id}/claim", response_model=ReviewItemResponse)
def claim_item(
    company_id: int,
    item_id: int,
    _company: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    return _transition_response(
        claim_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        user_id=user.id,
    )


@router.post("/{item_id}/release", response_model=ReviewItemResponse)
def release_item(
    company_id: int,
    item_id: int,
    _company: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    return _transition_response(
        release_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        user_id=user.id,
    )


@router.post("/{item_id}/reassign", response_model=ReviewItemResponse)
def reassign_item(
    company_id: int,
    item_id: int,
    request: ReviewItemReassignRequest,
    _company: Empresa = Depends(require_company_access("admin_empresa")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    target = db.get(Usuario, request.assignee_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=422, detail="Responsável inválido")
    has_company_operation = any(
        permission.empresa_id == company_id
        and permission.permissao in {"operacao", "admin_empresa"}
        for permission in target.permissoes_empresas
    )
    if target.papel != "admin" and not has_company_operation:
        raise HTTPException(status_code=422, detail="Responsável sem acesso operacional")
    return _transition_response(
        reassign_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        actor_id=user.id,
        assignee_id=target.id,
        reason=request.reason,
    )


@router.post("/{item_id}/resolve", response_model=ReviewItemResponse)
def resolve_item(
    company_id: int,
    item_id: int,
    _company: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    item = db.query(ReviewItem).filter(
        ReviewItem.id == item_id, ReviewItem.empresa_id == company_id
    ).first()
    if item is not None and item.source_type in {"snapshot_conflict", "razao_account_unknown"}:
        raise HTTPException(
            status_code=409,
            detail="Esta pendência exige uma decisão no fluxo específico da origem",
        )
    if item is not None and item.source_type in {"razao_snapshot_conflict", "razao_snapshot_missing"}:
        try:
            movement_date = date.fromisoformat(item.grouping_key)
            snapshot = selecionar_snapshot(
                db, empresa_id=company_id, competencia=movement_date
            )
        except (ValueError, SnapshotConflict) as exc:
            raise HTTPException(status_code=409, detail="Snapshot aplicável ainda indefinido") from exc
        if snapshot is None:
            raise HTTPException(status_code=409, detail="Snapshot aplicável ainda indefinido")
    return _transition_response(
        resolve_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        user_id=user.id,
    )


@router.post("/{item_id}/confirm-razao-alias", response_model=ReviewItemResponse)
def confirm_razao_alias_item(
    company_id: int,
    item_id: int,
    request: RazaoAliasConfirmationRequest,
    _company: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    try:
        confirmar_alias_razao(
            db,
            empresa_id=company_id,
            item_id=item_id,
            target_codigo=request.target_codigo,
            user_id=user.id,
            reason=request.reason,
        )
        db.commit()
        item = db.get(ReviewItem, item_id)
        return _response(item, user)
    except ReviewItemNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Pendência não encontrada") from exc
    except ReviewItemConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{item_id}/dismiss", response_model=ReviewItemResponse)
def dismiss_item(
    company_id: int,
    item_id: int,
    request: ReviewItemReasonRequest,
    _company: Empresa = Depends(require_company_access("operacao")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    item = db.query(ReviewItem).filter(
        ReviewItem.id == item_id, ReviewItem.empresa_id == company_id
    ).first()
    if item is not None and item.source_type in {"snapshot_conflict", "razao_snapshot_conflict"}:
        raise HTTPException(
            status_code=409,
            detail="Conflito de snapshot exige seleção e justificativa no fluxo do plano",
        )
    return _transition_response(
        dismiss_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        user_id=user.id,
        reason=request.reason,
    )


@router.post("/{item_id}/reopen", response_model=ReviewItemResponse)
def reopen_item(
    company_id: int,
    item_id: int,
    request: ReviewItemReasonRequest,
    _company: Empresa = Depends(require_company_access("admin_empresa")),
    user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> ReviewItemResponse:
    item = db.query(ReviewItem).filter(
        ReviewItem.id == item_id, ReviewItem.empresa_id == company_id
    ).first()
    if item is not None and item.source_type in {"snapshot_conflict", "razao_snapshot_conflict"}:
        raise HTTPException(status_code=409, detail="Decisão de snapshot não pode ser reaberta")
    return _transition_response(
        reopen_review_item,
        db=db,
        user=user,
        empresa_id=company_id,
        item_id=item_id,
        user_id=user.id,
        reason=request.reason,
    )
