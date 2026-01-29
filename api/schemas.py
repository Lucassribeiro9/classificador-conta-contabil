from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional


# Schemas para transação
class TransacaoBase(BaseModel):
    data: date
    cod_banco: Optional[int] = None
    descricao: str
    valor: float
    conta_contabil: Optional[int] = None
    empresa_id: int


class TransacaoCreate(TransacaoBase):
    pass


class Transacao(TransacaoBase):
    id: int
    empresa_id: int
    conta_contabil: Optional[int] = None
    confidence: Optional[float] = None
    needs_review: bool = False
    is_classified: bool = False
    created_at: datetime
    updated_at: datetime
    # Permite conversão de objetos ORM para Pydantic
    model_config = ConfigDict(from_attributes=True)


# Schema para empresa
class EmpresaBase(BaseModel):
    nome: str
    cnpj: str
    cod_dominio: int


class EmpresaCreate(EmpresaBase):
    pass


class Empresa(EmpresaBase):
    id: int
    api_key: str
    created_at: datetime
    updated_at: datetime
    # Permite conversão de objetos ORM para Pydantic
    model_config = ConfigDict(from_attributes=True)
