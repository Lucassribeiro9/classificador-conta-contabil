from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from core import models
from core.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(
    x_api_key: str = Header(..., description="API Key da empresa"),
    db: Session = Depends(get_db),
):
    # Verifica se possui a chave
    if not x_api_key:
        raise HTTPException(status_code=403, detail="API Key is required")
    # Procura a empresa que possui a chave
    empresa = (
        db.query(models.Empresa).filter(models.Empresa.api_key == x_api_key).first()
    )
    if not empresa:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return empresa
