from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.models import (
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    FechamentoRazaoMensal,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    WarningImportacaoRazao,
)
from core.razao_catalog_validator import validate_lancamento_razao_contas
from core.razao_parser import (
    normalize_lancamento_razao,
    normalize_razao_historico,
    parse_razao_xlsx,
    parse_razao_xlsx_with_metadata,
    RazaoParseError,
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
    block_size: int | None = None,
) -> ImportacaoRazaoResumo:
    if block_size is None:
        block_size = settings.RAZAO_IMPORT_BLOCK_SIZE
    if block_size <= 0:
        raise ValueError("O tamanho do bloco deve ser maior que zero.")
    file_path = Path(path)
    file_hash = _file_hash(file_path)
    _ensure_file_hash_not_successfully_imported(session, empresa_id, file_hash)
    parsed_lancamentos = _parse_lancamentos_and_validate_company(
        session,
        file_path,
        empresa_id,
    )
    warning_preview: list[dict[str, Any]] = []
    warning_preview_limit = 100
    warning_totals: dict[str, int] = {}
    imported = 0
    saldo_periodo_sequences: dict[str, Decimal] = {}
    saldo_exercicio_sequences: dict[str, Decimal] = {}
    saldo_absent_warnings: set[str] = set()
    fechamentos: dict[tuple[int, int, int, int], FechamentoRazaoMensal] = {}
    fechamento_warnings: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}

    lote = LoteImportacaoRazao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        original_filename=original_filename,
        file_hash=file_hash,
        status="processing",
        total_linhas=len(parsed_lancamentos),
        total_importadas=0,
        total_invalidas=0,
        warnings_metadata={"totals_by_code": {}},
    )
    session.add(lote)
    session.flush()

    catalog_codes = _preload_catalog_codes(session, parsed_lancamentos)
    account_links = _preload_account_links(session, empresa_id, catalog_codes)

    for block_start in range(0, len(parsed_lancamentos), block_size):
        models: list[LancamentoRazaoNormalizado] = []
        normalized_warnings: list[WarningImportacaoRazao] = []
        block_warnings: list[dict[str, Any]] = []
        block = parsed_lancamentos[block_start : block_start + block_size]
        for offset, parsed in enumerate(block, start=1):
            index = block_start + offset
            warning_start = len(block_warnings)
            try:
                normalized = normalize_lancamento_razao(parsed)
                normalized.update(_saldo_fields_from_parsed(parsed))
                normalized["bloco_id"] = parsed["bloco_id"]
                normalized["empresa_id"] = empresa_id
                normalized["numero_lancamento"] = normalized.pop("numero")
                if _is_blank(normalized.get("conta_contrapartida")):
                    block_warnings.append(
                        {
                            "linha": index,
                            "warnings": ["Linha do razao sem contrapartida valida."],
                        }
                    )
                    continue

                validation = validate_lancamento_razao_contas(
                    session, normalized, existing_codes=catalog_codes
                )
                if not validation.is_valid:
                    block_warnings.append(
                        {
                            "linha": index,
                            "warnings": validation.warnings,
                        }
                    )
                    continue

                normalized["historico_normalizado"] = normalize_razao_historico(
                    normalized["historico"]
                )
                models.append(_to_model(lote.id, empresa_id, normalized))
                _update_account_links(account_links, session, empresa_id, normalized)
                _update_fechamento_mensal(
                    session,
                    fechamentos,
                    fechamento_warnings,
                    saldo_periodo_sequences,
                    saldo_exercicio_sequences,
                    lote.id,
                    empresa_id,
                    normalized,
                    block_warnings,
                    saldo_absent_warnings,
                    index,
                )
                imported += 1
            except (RazaoParseError, ValueError, TypeError, InvalidOperation) as exc:
                message = _line_error_message(exc)
                block_warnings.append(
                    {
                        "linha": index,
                        "warnings": [message],
                    }
                )
            finally:
                for warning in block_warnings[warning_start:]:
                    normalized_warnings.extend(
                        _to_warning_models(lote.id, warning, warning_totals)
                    )

        if models:
            session.bulk_save_objects(models)
        if normalized_warnings:
            session.bulk_save_objects(normalized_warnings)
        lote.linhas_processadas = min(block_start + len(block), len(parsed_lancamentos))
        lote.total_importadas = imported
        lote.total_invalidas = lote.linhas_processadas - imported
        lote.warnings_total = sum(warning_totals.values())
        lote.warnings_metadata = {"totals_by_code": dict(warning_totals)}
        session.flush()
        preview_capacity = warning_preview_limit - len(warning_preview)
        if preview_capacity > 0:
            warning_preview.extend(block_warnings[:preview_capacity])

    invalid = len(parsed_lancamentos) - imported
    lote.total_importadas = imported
    lote.total_invalidas = invalid
    lote.warnings_total = sum(warning_totals.values())
    lote.warnings_metadata = {"totals_by_code": dict(warning_totals)}
    if invalid == 0 and lote.warnings_total == 0:
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
        warnings=warning_preview,
    )


def _parse_lancamentos_and_validate_company(
    session: Session,
    file_path: Path,
    empresa_id: int,
) -> list[dict[str, Any]]:
    try:
        parsed = parse_razao_xlsx_with_metadata(file_path)
    except RazaoParseError as exc:
        if not str(exc).startswith("Cabecalho do razao sem metadados obrigatorios"):
            raise
        return parse_razao_xlsx(file_path)

    _ensure_file_company_matches_target(
        session,
        empresa_id,
        parsed.metadata.cnpj_cpf,
    )
    return parsed.lancamentos


def _ensure_file_company_matches_target(
    session: Session,
    empresa_id: int,
    file_cnpj_cpf: str,
) -> None:
    empresa = session.get(Empresa, empresa_id)
    if empresa is None:
        raise RazaoImportError("Empresa da importacao nao encontrada.")
    if file_cnpj_cpf != empresa.cnpj_cpf:
        raise RazaoImportError(
            "CNPJ do razao nao corresponde a empresa da importacao."
        )
    if not empresa.is_active:
        raise RazaoImportError(
            "empresa do razao esta inativa; reative a empresa antes de importar."
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
        saldo_anterior_original=lancamento.get("saldo_anterior_original"),
        saldo_anterior_decimal=lancamento.get("saldo_anterior_decimal"),
        saldo_anterior_natureza=lancamento.get("saldo_anterior_natureza"),
        saldo_original=lancamento.get("saldo_original"),
        saldo_decimal=lancamento.get("saldo_decimal"),
        saldo_natureza=lancamento.get("saldo_natureza"),
        saldo_exercicio_original=lancamento.get("saldo_exercicio_original"),
        saldo_exercicio_decimal=lancamento.get("saldo_exercicio_decimal"),
        saldo_exercicio_natureza=lancamento.get("saldo_exercicio_natureza"),
    )


def _saldo_fields_from_parsed(lancamento: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for saldo_key, field_prefix in (
        ("saldo_anterior", "saldo_anterior"),
        ("saldo", "saldo"),
        ("saldo_exercicio", "saldo_exercicio"),
    ):
        saldo = lancamento.get(saldo_key)
        if not isinstance(saldo, dict):
            continue
        fields[f"{field_prefix}_original"] = saldo.get("valor_original")
        fields[f"{field_prefix}_decimal"] = saldo.get("valor_decimal")
        fields[f"{field_prefix}_natureza"] = saldo.get("natureza")
    return fields


def _update_fechamento_mensal(
    session: Session,
    fechamentos: dict[tuple[int, int, int, int], FechamentoRazaoMensal],
    fechamento_warnings: dict[tuple[int, int, int, int], list[dict[str, Any]]],
    saldo_periodo_sequences: dict[str, Decimal],
    saldo_exercicio_sequences: dict[str, Decimal],
    lote_id: int,
    empresa_id: int,
    lancamento: dict[str, Any],
    warnings: list[dict[str, Any]],
    saldo_absent_warnings: set[str],
    linha: int,
) -> None:
    """Atualiza sequencia, warnings e fechamento mensal de uma linha valida."""
    conta_codigo = int(lancamento["conta_origem"])
    bloco_id = str(lancamento["bloco_id"])
    data_lancamento = _parse_date(lancamento["data"])
    key = (empresa_id, conta_codigo, data_lancamento.year, data_lancamento.month)
    saldo_calculado_periodo = _calcula_saldo_lancamento(
        saldo_periodo_sequences,
        f"{bloco_id}:{data_lancamento.year}:{data_lancamento.month}",
        lancamento,
        incluir_saldo_anterior=False,
    )
    saldo_calculado_exercicio = _calcula_saldo_lancamento(
        saldo_exercicio_sequences,
        bloco_id,
        lancamento,
        incluir_saldo_anterior=True,
    )
    observed = _observed_sequence_balance(lancamento)
    structured_warning: dict[str, Any] | None = None

    if observed is None:
        if (
            lancamento.get("saldo_exercicio_original") is None
            and bloco_id not in saldo_absent_warnings
        ):
            mensagem = (
                "Saldo ausente; conferencia por saldo limitada para este bloco."
            )
            structured_warning = {
                "linha": linha,
                "codigo": "saldo_ausente",
                "mensagem": mensagem,
                "detalhes": {
                    "bloco_id": bloco_id,
                    "conta_codigo": conta_codigo,
                },
                "warnings": [mensagem],
            }
            saldo_absent_warnings.add(bloco_id)
    elif observed.get("decimal") is None or (
        observed["decimal"] != 0 and observed.get("natureza") not in {"D", "C"}
    ):
        mensagem = (
            "Saldo informado invalido; conferencia por saldo limitada para esta linha."
        )
        structured_warning = {
            "linha": linha,
            "codigo": "saldo_invalido",
            "mensagem": mensagem,
            "detalhes": {
                "bloco_id": bloco_id,
                "conta_codigo": conta_codigo,
                "saldo_calculado": _balance_payload(saldo_calculado_periodo),
                "saldo_observado": {
                    "fonte": "saldo",
                    "valor_original": observed.get("original"),
                    "valor_decimal": (
                        str(observed["decimal"])
                        if observed.get("decimal") is not None
                        else None
                    ),
                    "natureza": observed.get("natureza"),
                },
            },
            "warnings": [mensagem],
        }
    elif _signed_balance(observed["decimal"], observed["natureza"]) != saldo_calculado_periodo:
        mensagem = (
            "Saldo observado diverge do saldo calculado para a conta do razao."
        )
        structured_warning = {
            "linha": linha,
            "codigo": "saldo_divergente",
            "mensagem": mensagem,
            "detalhes": {
                "bloco_id": bloco_id,
                "conta_codigo": conta_codigo,
                "saldo_calculado": _balance_payload(saldo_calculado_periodo),
                "saldo_observado": {
                    "fonte": "saldo",
                    "valor_decimal": str(observed["decimal"]),
                    "natureza": observed["natureza"],
                },
            },
            "warnings": [mensagem],
        }

    if structured_warning is not None:
        warnings.append(structured_warning)
        fechamento_warnings.setdefault(key, []).append(structured_warning)
        fechamento_existente = fechamentos.get(key)
        if fechamento_existente is not None:
            fechamento_existente.warnings_saldo = list(fechamento_warnings[key])

    observed_source, closing_observed = _observed_closing_balance(lancamento)
    if closing_observed is None or closing_observed.get("decimal") is None:
        return

    fechamento = fechamentos.get(key)
    if fechamento is None:
        fechamento = FechamentoRazaoMensal(
            lote_id=lote_id,
            empresa_id=empresa_id,
            conta_codigo=conta_codigo,
            ano=data_lancamento.year,
            mes=data_lancamento.month,
            warnings_saldo=list(fechamento_warnings.get(key, [])),
        )
        fechamentos[key] = fechamento
        session.add(fechamento)

    fechamento.saldo_observado_original = closing_observed.get("original")
    fechamento.saldo_observado_decimal = closing_observed.get("decimal")
    fechamento.saldo_observado_natureza = closing_observed.get("natureza")
    fechamento.saldo_observado_fonte = observed_source
    fechamento.saldo_calculado_decimal = abs(
        saldo_calculado_exercicio
        if observed_source == "saldo_exercicio"
        else saldo_calculado_periodo
    )


def _calcula_saldo_lancamento(
    saldo_sequences: dict[str, Decimal],
    bloco_id: str,
    lancamento: dict[str, Any],
    *,
    incluir_saldo_anterior: bool,
) -> Decimal:
    """Aplica o lancamento ao saldo assinado e isolado do bloco."""
    if bloco_id not in saldo_sequences:
        saldo_sequences[bloco_id] = (
            _saldo_inicial(lancamento)
            if incluir_saldo_anterior
            else Decimal("0")
        )

    valor = Decimal(str(lancamento["valor"]))
    if lancamento["direcao"] == "debito":
        saldo_sequences[bloco_id] += valor
    else:
        saldo_sequences[bloco_id] -= valor
    return saldo_sequences[bloco_id]


def _saldo_inicial(lancamento: dict[str, Any]) -> Decimal:
    """Converte saldo anterior D/C para a representacao assinada."""
    valor = lancamento.get("saldo_anterior_decimal")
    natureza = lancamento.get("saldo_anterior_natureza")
    if valor is None or natureza not in {"D", "C"}:
        return Decimal("0")
    return _signed_balance(valor, natureza)


def _observed_sequence_balance(
    lancamento: dict[str, Any],
) -> dict[str, Any] | None:
    """Retorna somente o saldo que valida a sequencia exibida no Razao."""
    if lancamento.get("saldo_original") is None:
        return None
    return {
        "original": lancamento.get("saldo_original"),
        "decimal": lancamento.get("saldo_decimal"),
        "natureza": lancamento.get("saldo_natureza"),
    }


def _observed_closing_balance(
    lancamento: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    """Seleciona a referencia observada usada no fechamento mensal."""
    if lancamento.get("saldo_exercicio_decimal") is not None:
        return "saldo_exercicio", {
            "original": lancamento.get("saldo_exercicio_original"),
            "decimal": lancamento.get("saldo_exercicio_decimal"),
            "natureza": lancamento.get("saldo_exercicio_natureza"),
        }
    if lancamento.get("saldo_decimal") is not None:
        return "saldo", {
            "original": lancamento.get("saldo_original"),
            "decimal": lancamento.get("saldo_decimal"),
            "natureza": lancamento.get("saldo_natureza"),
        }
    return None, None


def _balance_payload(valor: Decimal) -> dict[str, str]:
    """Serializa um saldo assinado em valor absoluto e natureza D/C."""
    return {
        "valor_decimal": str(abs(valor)),
        "natureza": "C" if valor < 0 else "D",
    }


def _signed_balance(valor: Decimal, natureza: str | None) -> Decimal:
    if natureza == "C":
        return -abs(valor)
    return abs(valor)


def _preload_catalog_codes(
    session: Session,
    parsed_lancamentos: list[dict[str, Any]],
) -> set[int]:
    """Carrega em uma consulta todos os códigos potencialmente usados."""
    requested: set[int] = set()
    for parsed in parsed_lancamentos:
        for field in ("conta_origem", "contrapartida", "conta_contrapartida"):
            value = parsed.get(field)
            if _is_blank(value):
                continue
            try:
                requested.add(int(value))
            except (TypeError, ValueError):
                continue
    if not requested:
        return set()
    return set(
        session.execute(
            select(ContaContabil.codigo).where(ContaContabil.codigo.in_(requested))
        ).scalars()
    )


def _preload_account_links(
    session: Session,
    empresa_id: int,
    catalog_codes: set[int],
) -> dict[int, EmpresaContaContabil]:
    if not catalog_codes:
        return {}
    links = session.execute(
        select(EmpresaContaContabil).where(
            EmpresaContaContabil.empresa_id == empresa_id,
            EmpresaContaContabil.conta_codigo.in_(catalog_codes),
        )
    ).scalars()
    return {link.conta_codigo: link for link in links}


def _update_account_links(
    account_links: dict[int, EmpresaContaContabil],
    session: Session,
    empresa_id: int,
    lancamento: dict[str, Any],
) -> None:
    data_lancamento = _parse_date(lancamento["data"])
    for conta_codigo in {
        int(lancamento["conta_origem"]),
        int(lancamento["conta_contrapartida"]),
    }:
        vinculo = account_links.get(conta_codigo)
        if vinculo is None:
            vinculo = EmpresaContaContabil(
                empresa_id=empresa_id,
                conta_codigo=conta_codigo,
                quantidade_lancamentos=1,
                ultima_utilizacao=data_lancamento,
            )
            account_links[conta_codigo] = vinculo
            session.add(vinculo)
            continue

        vinculo.quantidade_lancamentos += 1
        if data_lancamento > vinculo.ultima_utilizacao:
            vinculo.ultima_utilizacao = data_lancamento


def _to_warning_models(
    lote_id: int,
    warning: dict[str, Any],
    totals: dict[str, int],
) -> list[WarningImportacaoRazao]:
    """Converte o aviso público em registro seguro e atualiza seu agregado."""
    messages = warning.get("warnings") or []
    explicit_message = warning.get("mensagem")
    if explicit_message is not None:
        messages = [explicit_message]
    elif not messages:
        messages = ["Aviso do razao."]
    details = warning.get("detalhes")
    if not isinstance(details, dict):
        details = {}
    models = []
    for raw_message in messages:
        message = str(raw_message)
        code = str(warning.get("codigo") or _warning_code(message))
        totals[code] = totals.get(code, 0) + 1
        models.append(
            WarningImportacaoRazao(
                lote_id=lote_id,
                linha=warning.get("linha"),
                codigo=code,
                mensagem=message,
                detalhes=details,
            )
        )
    return models


def _warning_code(message: str) -> str:
    if "sem contrapartida" in message:
        return "contrapartida_ausente"
    if "nao encontrada no catalogo" in message:
        return "conta_nao_encontrada"
    if message == "Data do lancamento invalida.":
        return "data_invalida"
    if message == "Valor do lancamento invalido.":
        return "valor_invalido"
    return "linha_invalida"


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _line_error_message(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, RazaoParseError):
        return message
    if "Invalid isoformat" in message:
        return "Data do lancamento invalida."
    if isinstance(exc, InvalidOperation):
        return "Valor do lancamento invalido."
    if "invalid literal for int" in message:
        return "Conta do lancamento invalida."
    return "Linha do razao invalida."


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
