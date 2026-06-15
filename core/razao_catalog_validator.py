from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import ContaContabil


@dataclass(frozen=True)
class RazaoAccountValidationResult:
    is_valid: bool
    warnings: list[str]


def validate_lancamento_razao_contas(
    session: Session,
    lancamento: dict[str, Any],
) -> RazaoAccountValidationResult:
    codigos = {
        int(lancamento["conta_origem"]),
        int(lancamento["conta_contrapartida"]),
    }
    existing_codes = set(
        session.execute(
            select(ContaContabil.codigo).where(ContaContabil.codigo.in_(codigos))
        ).scalars()
    )

    warnings = []
    if int(lancamento["conta_origem"]) not in existing_codes:
        warnings.append(
            f"Conta de origem {lancamento['conta_origem']} nao encontrada no catalogo."
        )
    if int(lancamento["conta_contrapartida"]) not in existing_codes:
        warnings.append(
            "Conta de contrapartida "
            f"{lancamento['conta_contrapartida']} nao encontrada no catalogo."
        )

    return RazaoAccountValidationResult(is_valid=not warnings, warnings=warnings)
