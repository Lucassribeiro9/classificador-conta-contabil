from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from core.config import settings
from core.models import Empresa
from core.database import SessionLocal

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
