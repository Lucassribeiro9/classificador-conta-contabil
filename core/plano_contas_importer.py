from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import ContaContabil
from core.plano_contas_financeiro import infer_is_financial_origin


@dataclass(frozen=True)
class ImportacaoPlanoContasResumo:
    criadas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0
    invalidas: int = 0


_REQUIRED_FIELDS = ("codigo", "classificacao", "nome", "tipo", "grau")


def import_plano_contas(
    session: Session,
    contas_normalizadas: list[dict[str, Any]],
) -> ImportacaoPlanoContasResumo:
    existing_by_codigo = {
        conta.codigo: conta
        for conta in session.execute(select(ContaContabil)).scalars().all()
    }

    criadas = 0
    atualizadas = 0
    ignoradas = 0
    invalidas = 0

    for raw_conta in contas_normalizadas:
        conta_data = _normalize_conta(raw_conta)
        if conta_data is None:
            invalidas += 1
            continue

        existing = existing_by_codigo.get(conta_data["codigo"])
        if existing is None:
            conta = ContaContabil(**conta_data)
            session.add(conta)
            existing_by_codigo[conta.codigo] = conta
            criadas += 1
            continue

        if _apply_changes(existing, conta_data):
            atualizadas += 1
        else:
            ignoradas += 1

    session.flush()
    return ImportacaoPlanoContasResumo(
        criadas=criadas,
        atualizadas=atualizadas,
        ignoradas=ignoradas,
        invalidas=invalidas,
    )


def _normalize_conta(raw_conta: dict[str, Any]) -> dict[str, Any] | None:
    if any(_is_blank(raw_conta.get(field)) for field in _REQUIRED_FIELDS):
        return None

    tipo = str(raw_conta["tipo"]).strip().upper()
    if tipo not in {"A", "S"}:
        return None

    try:
        codigo = int(raw_conta["codigo"])
        grau = int(raw_conta["grau"])
    except (TypeError, ValueError):
        return None

    return {
        "codigo": codigo,
        "classificacao": str(raw_conta["classificacao"]).strip(),
        "nome": str(raw_conta["nome"]).strip(),
        "tipo": tipo,
        "grau": grau,
        "is_financial_origin": _financial_origin_flag(raw_conta),
    }


def _apply_changes(conta: ContaContabil, conta_data: dict[str, Any]) -> bool:
    changed = False
    for field in (
        "classificacao",
        "nome",
        "tipo",
        "grau",
        "is_financial_origin",
    ):
        new_value = conta_data[field]
        if getattr(conta, field) != new_value:
            setattr(conta, field, new_value)
            changed = True

    return changed


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _financial_origin_flag(raw_conta: dict[str, Any]) -> bool:
    if "is_financial_origin" in raw_conta:
        return bool(raw_conta["is_financial_origin"])

    return infer_is_financial_origin(
        nome=str(raw_conta["nome"]),
        classificacao=str(raw_conta["classificacao"]),
    )
