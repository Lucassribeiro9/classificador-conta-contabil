from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_global_admin
from api.schemas import (
    UsuarioCreate,
    UsuarioEmpresaPermissaoCreate,
    UsuarioEmpresaPermissaoResponse,
    UsuarioResponse,
)
from core.models import Empresa, Usuario, UsuarioEmpresaPermissao


router = APIRouter(prefix="/admin/users")
password_hash = PasswordHash.recommended()


def _get_user_or_404(user_id: int, db: Session) -> Usuario:
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


def _get_company_or_404(company_id: int, db: Session) -> Empresa:
    company = db.get(Empresa, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company


def _get_permission_link(
    user_id: int,
    company_id: int,
    db: Session,
) -> UsuarioEmpresaPermissao | None:
    return (
        db.query(UsuarioEmpresaPermissao)
        .filter(
            UsuarioEmpresaPermissao.usuario_id == user_id,
            UsuarioEmpresaPermissao.empresa_id == company_id,
        )
        .first()
    )


@router.post("", response_model=UsuarioResponse)
def create_user(
    user: UsuarioCreate,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> Usuario:
    """Cria um usuario interno pelo painel administrativo.

    Requer usuario autenticado com papel `admin`, armazena apenas o hash da
    senha e nunca retorna segredo ou hash na resposta.
    """
    existing_user = (
        db.query(Usuario)
        .filter(or_(Usuario.login == user.login, Usuario.email == user.email))
        .first()
    )
    if existing_user:
        raise HTTPException(status_code=409, detail="Usuário já cadastrado")

    data = user.model_dump(exclude={"senha"})
    new_user = Usuario(
        **data,
        senha_hash=password_hash.hash(user.senha),
        is_active=True,
    )
    try:
        db.add(new_user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Usuário já cadastrado") from exc

    db.refresh(new_user)
    return new_user


@router.get("", response_model=list[UsuarioResponse])
def list_users(
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> list[Usuario]:
    """Lista usuarios internos para administradores.

    A resposta usa schema publico e omite senha e hash de senha.
    """
    return db.query(Usuario).order_by(Usuario.id).all()


@router.patch("/{user_id}/deactivate", response_model=UsuarioResponse)
def deactivate_user(
    user_id: int,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> Usuario:
    """Desativa um usuario interno.

    Requer usuario autenticado com papel `admin` e retorna `404` quando o
    usuario informado nao existe.
    """
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/activate", response_model=UsuarioResponse)
def activate_user(
    user_id: int,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> Usuario:
    """Reativa um usuario interno previamente desativado.

    Requer usuario autenticado com papel `admin` e retorna `404` quando o
    usuario informado nao existe.
    """
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/{user_id}/companies/{company_id}/permissions",
    response_model=UsuarioEmpresaPermissaoResponse,
)
def create_company_permission(
    user_id: int,
    company_id: int,
    permission: UsuarioEmpresaPermissaoCreate,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> UsuarioEmpresaPermissao:
    """Vincula um usuario a uma empresa com permissao operacional.

    Requer usuario autenticado com papel `admin`, valida existencia do usuario
    e da empresa e rejeita vinculo duplicado.
    """
    _get_user_or_404(user_id=user_id, db=db)
    _get_company_or_404(company_id=company_id, db=db)

    existing_link = _get_permission_link(
        user_id=user_id,
        company_id=company_id,
        db=db,
    )
    if existing_link is not None:
        raise HTTPException(status_code=409, detail="Vínculo já cadastrado")

    link = UsuarioEmpresaPermissao(
        usuario_id=user_id,
        empresa_id=company_id,
        permissao=permission.permissao,
    )
    try:
        db.add(link)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Vínculo já cadastrado") from exc

    db.refresh(link)
    return link


@router.patch(
    "/{user_id}/companies/{company_id}/permissions",
    response_model=UsuarioEmpresaPermissaoResponse,
)
def update_company_permission(
    user_id: int,
    company_id: int,
    permission: UsuarioEmpresaPermissaoCreate,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> UsuarioEmpresaPermissao:
    """Altera a permissao de um vinculo usuario-empresa existente."""
    link = _get_permission_link(user_id=user_id, company_id=company_id, db=db)
    if link is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    link.permissao = permission.permissao
    db.commit()
    db.refresh(link)
    return link


@router.delete(
    "/{user_id}/companies/{company_id}/permissions",
    status_code=204,
)
def delete_company_permission(
    user_id: int,
    company_id: int,
    _admin: Usuario = Depends(require_global_admin),
    db: Session = DB_DEPENDENCY,
) -> None:
    """Remove o vinculo de permissao entre usuario e empresa."""
    link = _get_permission_link(user_id=user_id, company_id=company_id, db=db)
    if link is None:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    db.delete(link)
    db.commit()
    return None
