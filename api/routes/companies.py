import secrets

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, require_admin_token
from api.schemas import Empresa as EmpresaSchema, EmpresaCreate
from core import models 

# Instanciando o router
router = APIRouter()

# Encontrar duplicatas
def _find_duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for value in values:
        if value in seen:
            duplicated.add(value)
        else:
            seen.add(value)
    return duplicated


# POST - Criar/Adicionar empresa
@router.post("/companies", response_model=EmpresaSchema)

def create_company(company: EmpresaCreate, _admin=Depends(require_admin_token), db: Session = DB_DEPENDENCY):
    # Criar empresa no banco de dados e gera uma api key única
    db_company = (
        db.query(models.Empresa)
        .filter(models.Empresa.cnpj_cpf == company.cnpj_cpf)
        .first()
    )
    if db_company:
        raise HTTPException(status_code=409, detail="Documento já cadastrado")
    # Criação do cadastro usando o modelo definido
    data_company = company.model_dump()
    data_company["api_key"] = f"sk_{secrets.token_hex(16)}"
    new_company = models.Empresa(**data_company)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


# POST - Criar/Adicionar empresas em lote
@router.post("/companies/batch", response_model=list[EmpresaSchema])
def create_companies_batch(companies: list[EmpresaCreate], _admin=Depends(require_admin_token), db: Session = DB_DEPENDENCY):
    """
    Cria uma lista de empresas no banco de dados. Se houver algum documento duplicado, ou algum documento
    já cadastrado, a API irá retornar um erro HTTP 400 com a lista de documentos duplicados ou já cadastrados.
    Se houver algum erro inesperado, a API irá retornar um erro HTTP 500 com uma mensagem de erro genérica.
    Se a criação for bem-sucedida, a API irá retornar a lista de empresas criadas com suas respectivas chaves API.
    """
    docs = [company.cnpj_cpf for company in companies]
    duplicated_docs = _find_duplicates(docs)
    if duplicated_docs:
        raise HTTPException(
            status_code=409, detail=f"Documento já cadastrado: {duplicated_docs}"
        )
    existing_docs = {
        row[0]
        for row in db.query(models.Empresa.cnpj_cpf).filter(models.Empresa.cnpj_cpf.in_(docs)).all()
    }
    if existing_docs:
        raise HTTPException(status_code=409, detail=f"Documento já cadastrado: {existing_docs}")
    # Criação do cadastro usando o modelo definido
    new_companies = []
    for company in companies:
        data_company = company.model_dump()
        data_company["api_key"] = f"sk_{secrets.token_hex(16)}"
        new_companies.append(models.Empresa(**data_company))
    try: 
        db.add_all(new_companies)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Documento já cadastrado")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao criar empresas")
    for company in new_companies:
        db.refresh(company)
    return new_companies
# GET - Listar todas
@router.get("/companies", response_model=list[EmpresaSchema])
def get_companies(_admin=Depends(require_admin_token), db: Session = DB_DEPENDENCY):
    return db.query(models.Empresa).all()


# GET - Listar empresa por ID
@router.get("/companies/{company_id}", response_model=EmpresaSchema)
def get_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return company

# DELETE - Deletar empresa e suas transações (possível apenas para o root)
@router.delete("/companies/{company_id}", status_code=204)
def delete_company(company_id: int, _admin=Depends(require_admin_token), db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    db.delete(company)
    db.commit()
    return

# PATCH - Desativar empresa
@router.patch("/companies/{company_id}/deactivate", response_model=EmpresaSchema)
def deactivate_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa já está desativada")
    company.is_active = False
    db.commit()
    db.refresh(company)
    return company

# PATCH - Ativar empresa
@router.patch("/companies/{company_id}/activate", response_model=EmpresaSchema)
def activate_company(company_id: int, db: Session = DB_DEPENDENCY):
    company = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if company.is_active:
        raise HTTPException(status_code=403, detail="Empresa já está ativa")
    company.is_active = True
    db.commit()
    db.refresh(company)
    return company
