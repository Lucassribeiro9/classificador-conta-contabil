from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Os parametros passados nos modelos devem ser iguais aos do banco de dados

# Atualizar a conta contábil caso o usuário tenha feito um feedback
class FeedbackUpdate(BaseModel):
    conta_contabil: int


# Schemas para transação
class TransacaoBase(BaseModel):
    data: date
    cod_banco: Optional[int] = None
    historico: str
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
    nome_empresa: str
    cnpj_cpf: str
    cod_dominio: int
    is_active: bool = True


class EmpresaCreate(EmpresaBase):
    pass


class Empresa(EmpresaBase):
    id: int
    api_key: str
    created_at: datetime
    # Permite conversão de objetos ORM para Pydantic
    model_config = ConfigDict(from_attributes=True)
