from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_global_admin
from api.schemas import UsuarioCreate, UsuarioResponse
from core.models import Usuario


router = APIRouter(prefix="/admin/users")
password_hash = PasswordHash.recommended()


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
