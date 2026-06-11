from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pwdlib import PasswordHash
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY
from api.schemas import LoginRequest, TokenResponse
from core.config import settings
from core.models import Usuario


router = APIRouter(prefix="/auth")
password_hash = PasswordHash.recommended()
ACCESS_TOKEN_EXPIRES_IN_SECONDS = 12 * 60 * 60


def _create_access_token(usuario: Usuario) -> TokenResponse:
    """Gera um access token JWT para o usuario autenticado.

    O token segue a spec de auth:
    - algoritmo configurado em `JWT_ALGORITHM`;
    - segredo vindo de `JWT_SECRET_KEY`;
    - claims minimos `sub`, `role`, `type`, `iat` e `exp`;
    - expiracao fixa de 12 horas, sem refresh token.
    """
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(seconds=ACCESS_TOKEN_EXPIRES_IN_SECONDS)
    access_token = jwt.encode(
        {
            "sub": str(usuario.id),
            "role": usuario.papel,
            "type": "access",
            "iat": issued_at,
            "exp": expires_at,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRES_IN_SECONDS,
    )


def login_for_access_token(
    credentials: LoginRequest,
    db: Session = DB_DEPENDENCY,
) -> TokenResponse:
    """Autentica um usuario interno e retorna um access token bearer.

    Aceita login ou e-mail no campo `login`, valida a senha contra o hash
    armazenado e bloqueia usuarios inativos.

    Retorna:
    - `401` para usuario inexistente ou senha invalida, sem revelar qual caso ocorreu;
    - `403` para usuario inativo.
    """
    usuario = (
        db.query(Usuario)
        .filter(or_(Usuario.login == credentials.login, Usuario.email == credentials.login))
        .first()
    )
    if usuario is None or not password_hash.verify(
        credentials.senha,
        usuario.senha_hash if usuario is not None else "",
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    return _create_access_token(usuario)


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = DB_DEPENDENCY) -> TokenResponse:
    """Realiza login JWT de usuarios internos.

    Retorna apenas access token com expiracao de 12 horas. Refresh token fica
    fora do escopo desta primeira versao.
    """
    return login_for_access_token(credentials=credentials, db=db)
