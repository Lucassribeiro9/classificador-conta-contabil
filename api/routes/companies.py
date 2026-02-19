import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY
from api.schemas import Empresa, EmpresaCreate
from core import models

# Instanciando o router
router = APIRouter()


# POST - Criar/Adicionar empresa
@router.post("/companies", response_model=Empresa)
# trunk-ignore(trunk/ignore-does-nothing)
# trunk-ignore(ruff/B008)
def create_company(company: EmpresaCreate, db: Session = DB_DEPENDENCY):
    # Criar empresa no banco de dados e gera uma api key única
    db_company = (
        db.query(models.Empresa)
        .filter(models.Empresa.cnpj_cpf == company.cnpj_cpf)
        .first()
    )
    if db_company:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado")
    # Criação do cadastro usando o modelo definido
    data_company = company.model_dump()
    data_company["api_key"] = f"sk_{secrets.token_hex(16)}"
    new_company = models.Empresa(**data_company)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


# GET - Listar todas
@router.get("/companies", response_model=list[Empresa])
def get_companies(db: Session = DB_DEPENDENCY):
    return db.query(models.Empresa).all()


# GET - Listar empresa por ID
@router.get("/companies/{company_id}", response_model=Empresa)
def get_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company

# DELETE - Deletar empresa e suas transações (possível apenas para o root)
@router.delete("/companies/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    db.delete(company)
    db.commit()
    return

# PATCH - Desativar empresa
@router.patch("/companies/{company_id}/deactivate", response_model=Empresa)
def deactivate_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not company.is_active:
        raise HTTPException(status_code=400, detail="Empresa já está desativada")
    company.is_active = False
    db.commit()
    db.refresh(company)
    return company

# PATCH - Ativar empresa
@router.patch("/companies/{company_id}/activate", response_model=Empresa)
def activate_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if company.is_active:
        raise HTTPException(status_code=400, detail="Empresa já está ativa")
    company.is_active = True
    db.commit()
    db.refresh(company)
    return company
