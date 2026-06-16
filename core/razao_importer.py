from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import (
    EmpresaContaContabil,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
)
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


class RazaoImportError(ValueError):
    """Erro de validacao da importacao do razao."""


def import_razao(
    session: Session,
    path: str | Path,
    *,
    empresa_id: int,
    usuario_id: int,
    original_filename: str,
) -> ImportacaoRazaoResumo:
    file_path = Path(path)
    file_hash = _file_hash(file_path)
    _ensure_file_hash_not_successfully_imported(session, empresa_id, file_hash)
    parsed_lancamentos = parse_razao_xlsx(file_path)
    warnings: list[dict[str, Any]] = []
    imported = 0

    lote = LoteImportacaoRazao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        original_filename=original_filename,
        file_hash=file_hash,
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
        _link_contas_to_empresa(session, empresa_id, normalized)
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


def _link_contas_to_empresa(
    session: Session,
    empresa_id: int,
    lancamento: dict[str, Any],
) -> None:
    data_lancamento = _parse_date(lancamento["data"])
    for conta_codigo in {
        int(lancamento["conta_origem"]),
        int(lancamento["conta_contrapartida"]),
    }:
        vinculo = session.execute(
            select(EmpresaContaContabil).where(
                EmpresaContaContabil.empresa_id == empresa_id,
                EmpresaContaContabil.conta_codigo == conta_codigo,
            )
        ).scalar_one_or_none()
        if vinculo is None:
            session.add(
                EmpresaContaContabil(
                    empresa_id=empresa_id,
                    conta_codigo=conta_codigo,
                    quantidade_lancamentos=1,
                    ultima_utilizacao=data_lancamento,
                )
            )
            continue

        vinculo.quantidade_lancamentos += 1
        if data_lancamento > vinculo.ultima_utilizacao:
            vinculo.ultima_utilizacao = data_lancamento


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _ensure_file_hash_not_successfully_imported(
    session: Session,
    empresa_id: int,
    file_hash: str,
) -> None:
    existing_lote = session.execute(
        select(LoteImportacaoRazao).where(
            LoteImportacaoRazao.empresa_id == empresa_id,
            LoteImportacaoRazao.file_hash == file_hash,
            LoteImportacaoRazao.status.in_(
                ["completed", "completed_with_warnings"]
            ),
        )
    ).scalar_one_or_none()
    if existing_lote is not None:
        raise RazaoImportError(
            "Arquivo ja importado com sucesso para esta empresa."
        )


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
