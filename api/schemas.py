from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Os parametros passados nos modelos devem ser iguais aos do banco de dados

ALLOWED_USER_ROLES = {"admin", "contador", "operador"}
ALLOWED_COMPANY_PERMISSIONS = {"leitura", "operacao", "admin_empresa"}


def normalize_optional_int(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip() in ("", "0"):
        return None
    if value == 0:
        return None
    return value


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

    @field_validator("cod_banco", "conta_contabil", mode="before")
    @classmethod
    def normalize_empty_optional_numbers(cls, value):
        return normalize_optional_int(value)


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


class LoginRequest(BaseModel):
    login: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UsuarioCreate(BaseModel):
    nome: str
    login: str
    email: str
    senha: str
    papel: str

    @field_validator("papel")
    @classmethod
    def validate_papel(cls, value: str) -> str:
        if value not in ALLOWED_USER_ROLES:
            raise ValueError("Papel de usuário inválido")
        return value


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    login: str
    email: str
    papel: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UsuarioEmpresaPermissaoCreate(BaseModel):
    permissao: str

    @field_validator("permissao")
    @classmethod
    def validate_permissao(cls, value: str) -> str:
        if value not in ALLOWED_COMPANY_PERMISSIONS:
            raise ValueError("Permissão inválida")
        return value


class UsuarioEmpresaPermissaoResponse(BaseModel):
    id: int
    usuario_id: int
    empresa_id: int
    permissao: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Schemas para predição
class PredictInput(BaseModel):
    historico: str
    cod_banco: Optional[int] = None

    @field_validator("cod_banco", mode="before")
    @classmethod
    def normalize_empty_cod_banco(cls, value):
        return normalize_optional_int(value)


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
