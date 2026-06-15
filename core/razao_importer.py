from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from core.models import LancamentoRazaoNormalizado, LoteImportacaoRazao
from core.razao_catalog_validator import validate_lancamento_razao_contas
from core.razao_parser import (
    normalize_lancamento_razao,
    normalize_razao_historico,
    parse_razao_xlsx,
)


@dataclass(frozen=True)
class ImportacaoRazaoResumo:
    lote_id: int
    status: str
    total_linhas: int
    total_importadas: int
    total_invalidas: int
    warnings: list[dict[str, Any]]


def import_razao(
    session: Session,
    path: str | Path,
    *,
    empresa_id: int,
    usuario_id: int,
    original_filename: str,
) -> ImportacaoRazaoResumo:
    file_path = Path(path)
    parsed_lancamentos = parse_razao_xlsx(file_path)
    warnings: list[dict[str, Any]] = []
    imported = 0

    lote = LoteImportacaoRazao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        original_filename=original_filename,
        file_hash=_file_hash(file_path),
        status="processing",
        total_linhas=len(parsed_lancamentos),
        total_importadas=0,
        total_invalidas=0,
        warnings_metadata={"warnings": []},
    )
    session.add(lote)
    session.flush()

    for index, parsed in enumerate(parsed_lancamentos, start=1):
        normalized = normalize_lancamento_razao(parsed)
        normalized["empresa_id"] = empresa_id
        normalized["numero_lancamento"] = normalized.pop("numero")
        if _is_blank(normalized.get("conta_contrapartida")):
            warnings.append(
                {
                    "linha": index,
                    "warnings": ["Linha do razao sem contrapartida valida."],
                }
            )
            continue

        validation = validate_lancamento_razao_contas(session, normalized)
        if not validation.is_valid:
            warnings.append({"linha": index, "warnings": validation.warnings})
            continue

        normalized["historico_normalizado"] = normalize_razao_historico(
            normalized["historico"]
        )
        session.add(_to_model(lote.id, empresa_id, normalized))
        imported += 1

    invalid = len(parsed_lancamentos) - imported
    lote.total_importadas = imported
    lote.total_invalidas = invalid
    lote.warnings_metadata = {"warnings": warnings}
    if invalid == 0:
        lote.status = "completed"
    elif imported > 0:
        lote.status = "completed_with_warnings"
    else:
        lote.status = "failed"

    session.flush()
    return ImportacaoRazaoResumo(
        lote_id=lote.id,
        status=lote.status,
        total_linhas=lote.total_linhas,
        total_importadas=lote.total_importadas,
        total_invalidas=lote.total_invalidas,
        warnings=warnings,
    )


def _to_model(
    lote_id: int,
    empresa_id: int,
    lancamento: dict[str, Any],
) -> LancamentoRazaoNormalizado:
    return LancamentoRazaoNormalizado(
        lote_id=lote_id,
        empresa_id=empresa_id,
        numero_lancamento=str(lancamento["numero_lancamento"]),
        data=_parse_date(lancamento["data"]),
        conta_origem=int(lancamento["conta_origem"]),
        conta_contrapartida=int(lancamento["conta_contrapartida"]),
        conta_debito=int(lancamento["conta_debito"]),
        conta_credito=int(lancamento["conta_credito"]),
        direcao=str(lancamento["direcao"]),
        historico=str(lancamento["historico"]),
        historico_normalizado=str(lancamento["historico_normalizado"]),
        valor=Decimal(str(lancamento["valor"])),
    )


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
