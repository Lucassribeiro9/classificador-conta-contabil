from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

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


class TransacaoListResponse(BaseModel):
    items: list[Transacao]
    total: int
    page: int
    limit: int
    has_next: bool


# Schema para empresa
class EmpresaBase(BaseModel):
    nome_empresa: str
    cnpj_cpf: str
    cod_dominio: int
    is_active: bool = True

    @field_validator("cnpj_cpf")
    @classmethod
    def validate_cnpj_cpf(cls, value: str) -> str:
        normalized = "".join(char for char in value if char.isdigit())
        if len(normalized) not in (11, 14):
            raise ValueError("CNPJ/CPF deve conter 11 ou 14 dígitos")
        return normalized
class EmpresaCreate(EmpresaBase):
    pass


class Empresa(EmpresaBase):
    id: int
    api_key: str
    created_at: datetime
    # Permite conversão de objetos ORM para Pydantic
    model_config = ConfigDict(from_attributes=True)


# Schemas para predição
class PredictInput(BaseModel):
    historico: str
    cod_banco: Optional[int] = None


class PredictResult(BaseModel):
    conta_contabil_predita: int
    confidence: float
    needs_review: bool
    historico: str
    cod_banco: Optional[int] = None


class PredictResponse(BaseModel):
    empresa_id: int
    quantidade_processada: int
    persisted: bool
    results: list[PredictResult]
