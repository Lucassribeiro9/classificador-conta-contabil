from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from core.models import Empresa
from core.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DB_DEPENDENCY = Depends(get_db)


def verify_api_key(
    x_api_key: str = Header(..., description="API Key da empresa"),
    db: Session = DB_DEPENDENCY,
):
    # Verifica se possui a chave
    """
    Verifica se a chave fornecida é válida e retorna a empresa correspondente.

    Se a chave for nula, retorna 403 com a mensagem "API Key is required".
    Se a chave for inválida, retorna 403 com a mensagem "Invalid API Key".
    """
    if not x_api_key:
        raise HTTPException(status_code=403, detail="API Key is required")
    # Procura a empresa que possui a chave
    empresa = db.query(Empresa).filter(Empresa.api_key == x_api_key).first()
    if not empresa:
        raise HTTPException(status_code=403, detail="Invalid API Key")
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
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")
    if route_company.id != empresa.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return route_company
