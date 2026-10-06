"""Leitura contextual de identidades contabeis e referencias legadas."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import ContaContabil, ContaContabilEmpresa, EmpresaContaContabil


_IDENTITY_FIELDS = (
    "classificacao",
    "nome",
    "tipo",
    "grau",
    "is_active",
    "is_financial_origin",
)


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


def garantir_identidade_contabil(
    session: Session, *, empresa_id: int, codigo: int
) -> ContaContabilEmpresa | None:
    """Resolve ou cria uma identidade empresarial a partir do catálogo legado.

    Uma identidade já existente sempre prevalece e nunca é sobrescrita pelos
    atributos globais. A criação mantém o contrato de compatibilidade enquanto
    consumidores ainda recebem códigos contábeis.
    """
    if empresa_id is None:
        raise ValueError("empresa_id obrigatorio")
    identidade = session.scalar(
        select(ContaContabilEmpresa).where(
            ContaContabilEmpresa.empresa_id == empresa_id,
            ContaContabilEmpresa.codigo == codigo,
        )
    )
    if identidade is not None:
        return identidade

    legado = session.scalar(
        select(ContaContabil).where(ContaContabil.codigo == codigo)
    )
    if legado is None:
        return None

    values = {
        "empresa_id": empresa_id,
        "codigo": legado.codigo,
        **{field: getattr(legado, field) for field in _IDENTITY_FIELDS},
    }
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert

        identity_id = session.scalar(
            insert(ContaContabilEmpresa)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["empresa_id", "codigo"])
            .returning(ContaContabilEmpresa.id)
        )
        if identity_id is not None:
            return session.get(ContaContabilEmpresa, identity_id)
        return session.scalar(
            select(ContaContabilEmpresa).where(
                ContaContabilEmpresa.empresa_id == empresa_id,
                ContaContabilEmpresa.codigo == codigo,
            )
        )

    identidade = ContaContabilEmpresa(**values)
    session.add(identidade)
    session.flush()
    return identidade


def listar_contas_contabeis(
    session: Session,
    *,
    empresa_id: int,
    codigo: int | None = None,
    nome: str | None = None,
    tipo: str | None = None,
    is_active: bool | None = None,
    is_financial_origin: bool | None = None,
) -> list[ContaContabilContextual]:
    """Lista identidades da empresa e completa lacunas com vínculos legados."""
    if empresa_id is None:
        raise ValueError("empresa_id obrigatorio")

    query = select(ContaContabilEmpresa).where(
        ContaContabilEmpresa.empresa_id == empresa_id
    )
    if codigo is not None:
        query = query.where(ContaContabilEmpresa.codigo == codigo)
    if nome is not None:
        query = query.where(ContaContabilEmpresa.nome.ilike(f"%{nome}%"))
    if tipo is not None:
        query = query.where(ContaContabilEmpresa.tipo == tipo.upper())
    if is_active is not None:
        query = query.where(ContaContabilEmpresa.is_active == is_active)
    if is_financial_origin is not None:
        query = query.where(
            ContaContabilEmpresa.is_financial_origin == is_financial_origin
        )
    identidades = session.scalars(
        query.order_by(ContaContabilEmpresa.codigo.asc())
    ).all()
    resultados = [_contexto_empresa(conta) for conta in identidades]

    codigos_empresariais = {conta.codigo for conta in identidades}
    legado_query = (
        select(ContaContabil)
        .join(
            EmpresaContaContabil,
            EmpresaContaContabil.conta_codigo == ContaContabil.codigo,
        )
        .where(EmpresaContaContabil.empresa_id == empresa_id)
    )
    if codigos_empresariais:
        legado_query = legado_query.where(
            ContaContabil.codigo.not_in(codigos_empresariais)
        )
    if codigo is not None:
        legado_query = legado_query.where(ContaContabil.codigo == codigo)
    if nome is not None:
        legado_query = legado_query.where(ContaContabil.nome.ilike(f"%{nome}%"))
    if tipo is not None:
        legado_query = legado_query.where(ContaContabil.tipo == tipo.upper())
    if is_active is not None:
        legado_query = legado_query.where(ContaContabil.is_active == is_active)
    if is_financial_origin is not None:
        legado_query = legado_query.where(
            ContaContabil.is_financial_origin == is_financial_origin
        )
    legadas = session.scalars(legado_query.order_by(ContaContabil.codigo.asc())).all()
    resultados.extend(_contexto_legado(empresa_id, conta) for conta in legadas)
    return sorted(resultados, key=lambda conta: conta.codigo)


def resolver_contas_contabeis(
    session: Session, *, empresa_id: int, codigos: set[int]
) -> dict[int, ContaContabilContextual]:
    """Resolve um conjunto de códigos sem permitir identidade de outra empresa."""
    if empresa_id is None:
        raise ValueError("empresa_id obrigatorio")
    if not codigos:
        return {}

    identidades = session.scalars(
        select(ContaContabilEmpresa).where(
            ContaContabilEmpresa.empresa_id == empresa_id,
            ContaContabilEmpresa.codigo.in_(codigos),
        )
    ).all()
    resultado = {
        conta.codigo: _contexto_empresa(conta) for conta in identidades
    }
    faltantes = codigos - set(resultado)
    if not faltantes:
        return resultado

    legadas = session.scalars(
        select(ContaContabil)
        .join(
            EmpresaContaContabil,
            EmpresaContaContabil.conta_codigo == ContaContabil.codigo,
        )
        .where(
            EmpresaContaContabil.empresa_id == empresa_id,
            ContaContabil.codigo.in_(faltantes),
        )
    ).all()
    resultado.update(
        {
            conta.codigo: _contexto_legado(empresa_id, conta)
            for conta in legadas
        }
    )
    return resultado


def _contexto_empresa(conta: ContaContabilEmpresa) -> ContaContabilContextual:
    return ContaContabilContextual(
        empresa_id=conta.empresa_id,
        id=conta.id,
        legacy_id=None,
        origem="empresa",
        codigo=conta.codigo,
        classificacao=conta.classificacao,
        nome=conta.nome,
        tipo=conta.tipo,
        grau=conta.grau,
        is_active=conta.is_active,
        is_financial_origin=conta.is_financial_origin,
        created_at=conta.created_at,
        updated_at=conta.updated_at,
    )


def _contexto_legado(
    empresa_id: int, conta: ContaContabil
) -> ContaContabilContextual:
    return ContaContabilContextual(
        empresa_id=empresa_id,
        id=None,
        legacy_id=conta.id,
        origem="legado",
        codigo=conta.codigo,
        classificacao=conta.classificacao,
        nome=conta.nome,
        tipo=conta.tipo,
        grau=conta.grau,
        is_active=conta.is_active,
        is_financial_origin=conta.is_financial_origin,
        created_at=conta.created_at,
        updated_at=conta.updated_at,
    )


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
        return _contexto_empresa(conta)

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
    return _contexto_legado(empresa_id, legado)
