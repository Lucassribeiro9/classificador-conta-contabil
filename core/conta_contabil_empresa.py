"""Leitura contextual de identidades contabeis e referencias legadas."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import ContaContabil, ContaContabilEmpresa, EmpresaContaContabil


@dataclass(frozen=True)
class ContaContabilContextual:
    empresa_id: int
    id: int | None
    legacy_id: int | None
    origem: str
    codigo: int
    classificacao: str
    nome: str
    tipo: str
    grau: int
    is_active: bool
    is_financial_origin: bool
    created_at: datetime
    updated_at: datetime


def resolver_conta_contabil(
    session: Session, *, empresa_id: int, codigo: int
) -> ContaContabilContextual | None:
    """Prioriza identidade da empresa; legado exige vinculo dessa empresa."""
    if empresa_id is None:
        raise ValueError("empresa_id obrigatorio")
    conta = session.scalar(
        select(ContaContabilEmpresa).where(
            ContaContabilEmpresa.empresa_id == empresa_id,
            ContaContabilEmpresa.codigo == codigo,
        )
    )
    if conta is not None:
        return ContaContabilContextual(
            empresa_id=empresa_id, id=conta.id, legacy_id=None, origem="empresa",
            codigo=conta.codigo, classificacao=conta.classificacao, nome=conta.nome,
            tipo=conta.tipo, grau=conta.grau, is_active=conta.is_active,
            is_financial_origin=conta.is_financial_origin,
            created_at=conta.created_at, updated_at=conta.updated_at,
        )

    legado = session.scalar(
        select(ContaContabil)
        .join(EmpresaContaContabil, EmpresaContaContabil.conta_codigo == ContaContabil.codigo)
        .where(
            EmpresaContaContabil.empresa_id == empresa_id,
            ContaContabil.codigo == codigo,
        )
    )
    if legado is None:
        return None
    return ContaContabilContextual(
        empresa_id=empresa_id, id=None, legacy_id=legado.id, origem="legado",
        codigo=legado.codigo, classificacao=legado.classificacao, nome=legado.nome,
        tipo=legado.tipo, grau=legado.grau, is_active=legado.is_active,
        is_financial_origin=legado.is_financial_origin,
        created_at=legado.created_at, updated_at=legado.updated_at,
    )
