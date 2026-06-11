import jwt
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.orm import Session
from core.config import settings
from core.models import Empresa, Usuario
from core.database import SessionLocal

bearer_scheme = HTTPBearer()
PERMISSION_LEVELS = {
    "leitura": 1,
    "operacao": 2,
    "admin_empresa": 3,
}

def require_admin_token(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    if not x_admin_token:
        raise HTTPException(status_code=401, detail="Admin token ausente")
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token inválido")    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB_DEPENDENCY = Depends(get_db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = DB_DEPENDENCY,
) -> Usuario:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expirado") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Token inválido")

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    if not usuario.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    return usuario


def _has_minimum_permission(actual: str, required: str) -> bool:
    return PERMISSION_LEVELS[actual] >= PERMISSION_LEVELS[required]


def require_company_access(required_permission: str) -> Callable:
    """Cria uma dependencia para validar acesso do usuario atual a uma empresa.

    A permissao minima deve ser uma das permissoes aprovadas na spec:
    `leitura`, `operacao` ou `admin_empresa`.

    Regras:
    - usuarios `admin` globais acessam a empresa sem vinculo explicito;
    - usuarios sem vinculo recebem `403`;
    - usuarios com permissao abaixo da exigida recebem `403`;
    - empresa inexistente retorna `404`.
    """
    if required_permission not in PERMISSION_LEVELS:
        raise ValueError("Permissão mínima inválida")

    def dependency(
        company_id: int,
        current_user: Usuario = Depends(get_current_user),
        db: Session = DB_DEPENDENCY,
    ) -> Empresa:
        empresa = db.get(Empresa, company_id)
        if empresa is None:
            raise HTTPException(status_code=404, detail="Empresa não encontrada")

        if current_user.papel == "admin":
            return empresa

        permission_link = next(
            (
                permission
                for permission in current_user.permissoes_empresas
                if permission.empresa_id == company_id
            ),
            None,
        )
        if permission_link is None:
            raise HTTPException(status_code=403, detail="Acesso negado")

        if not _has_minimum_permission(
            actual=permission_link.permissao,
            required=required_permission,
        ):
            raise HTTPException(status_code=403, detail="Permissão insuficiente")

        return empresa

    return dependency


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key", description="API Key da empresa"),
    db: Session = DB_DEPENDENCY,
):
    # Verifica se possui a chave
    """
    Verifica se a chave fornecida é válida e retorna a empresa correspondente.

    Se a chave for nula, retorna 401 com a mensagem "API Key ausente".
    Se a chave for inválida, retorna 403 com a mensagem "API Key inválida".
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API Key ausente")
    # Procura a empresa que possui a chave
    empresa = db.query(Empresa).filter(Empresa.api_key == x_api_key).first()
    if not empresa:
        raise HTTPException(status_code=403, detail="API Key inválida")
    return empresa


# Verificar empresa
def verify_company(
    company_id: int,
    empresa: Empresa = Depends(verify_api_key),
    db: Session = DB_DEPENDENCY,
):
    """
    Verifica se a empresa atual (obtida pela API Key) tem acesso a empresa de ID especificada.
    Se a empresa nao for encontrada, retorna 404. Se a empresa atual nao tem acesso a empresa especificada, retorna 403.
    """
    route_company = db.query(Empresa).filter(Empresa.id == company_id).first()
    if not route_company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if route_company.id != empresa.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return route_company
