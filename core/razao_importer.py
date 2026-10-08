from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, BinaryIO, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.models import (
    ContaContabil,
    ContaContabilEmpresa,
    Empresa,
    EmpresaContaContabil,
    FechamentoRazaoMensal,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    PlanoContasSnapshotEntry,
    PlanoContasImportEvent,
    PlanoContasSnapshot,
    RazaoAccountAlias,
    ReviewItem,
    WarningImportacaoRazao,
)
from core.plano_contas_snapshots import SnapshotConflict, selecionar_snapshot
from core.razao_catalog_validator import validate_lancamento_razao_contas
from core.review_items import create_review_item
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
    warnings_total: int = 0
    warnings_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class _SnapshotAccountContext:
    snapshot_id: int
    account_names: dict[int, str]
    account_codes: set[int]
    alias_codes: set[int]
    name_candidates: dict[str, list[int]]


class RazaoImportError(ValueError):
    """Erro de validacao da importacao do razao."""


def import_razao(
    session: Session,
    path: str | Path | BinaryIO,
    *,
    empresa_id: int,
    usuario_id: int | None,
    original_filename: str,
    block_size: int | None = None,
    existing_lote: LoteImportacaoRazao | None = None,
    progress: Callable[..., None] | None = None,
) -> ImportacaoRazaoResumo:
    if block_size is None:
        block_size = settings.RAZAO_IMPORT_BLOCK_SIZE
    if block_size <= 0:
        raise ValueError("O tamanho do bloco deve ser maior que zero.")
    owns_lote = existing_lote is None
    if owns_lote:
        file_hash = _file_hash(path)
        _ensure_file_hash_not_successfully_imported(session, empresa_id, file_hash)
    parsed_lancamentos = _parse_lancamentos_and_validate_company(
        session,
        path,
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

    if owns_lote:
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
    else:
        lote = existing_lote
        if lote.empresa_id != empresa_id:
            raise RazaoImportError("Lote não pertence à empresa da importação.")

    catalog_accounts = _preload_catalog_accounts(session, parsed_lancamentos)
    catalog_codes = set(catalog_accounts)
    has_company_snapshots = session.scalar(
        select(PlanoContasImportEvent.id)
        .where(PlanoContasImportEvent.empresa_id == empresa_id)
        .limit(1)
    ) is not None
    if has_company_snapshots:
        account_identities = {
            identity.codigo: identity
            for identity in session.scalars(
                select(ContaContabilEmpresa).where(
                    ContaContabilEmpresa.empresa_id == empresa_id,
                    ContaContabilEmpresa.codigo.in_(catalog_codes),
                )
            ).all()
        }
    else:
        account_identities = _ensure_company_account_identities(
            session, empresa_id, catalog_accounts
        )
    account_links = _preload_account_links(session, empresa_id, catalog_codes)
    snapshot_codes_by_date: dict[date, _SnapshotAccountContext | None | str] = {}
    snapshot_context_by_id: dict[int, _SnapshotAccountContext] = {}
    review_group_keys: dict[tuple[str, str], str] = {}

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

                movement_date = _parse_date(normalized["data"])
                if movement_date not in snapshot_codes_by_date:
                    try:
                        snapshot = selecionar_snapshot(
                            session, empresa_id=empresa_id, competencia=movement_date
                        )
                    except SnapshotConflict:
                        snapshot_codes_by_date[movement_date] = "conflict"
                    else:
                        if snapshot is None:
                            snapshot_codes_by_date[movement_date] = None
                        else:
                            if snapshot.id not in snapshot_context_by_id:
                                snapshot_context_by_id[snapshot.id] = _load_snapshot_account_context(
                                    session, empresa_id, snapshot
                                )
                            snapshot_codes_by_date[movement_date] = snapshot_context_by_id[snapshot.id]
                snapshot_context = snapshot_codes_by_date[movement_date]
                if snapshot_context == "conflict":
                    _create_razao_review_item(
                        session,
                        review_group_keys,
                        empresa_id=empresa_id,
                        source_type="razao_snapshot_conflict",
                        grouping_key=movement_date.isoformat(),
                        summary=f"Vigência do plano indefinida em {movement_date.isoformat()}",
                        criticality="critical",
                        evidence=[{
                            "source_type": "razao_line",
                            "source_id": f"{lote.id}:{index}",
                            "summary": f"Lote {lote.id}, linha {index}",
                        }],
                    )
                elif snapshot_context is None and has_company_snapshots:
                    _create_razao_review_item(
                        session,
                        review_group_keys,
                        empresa_id=empresa_id,
                        source_type="razao_snapshot_missing",
                        grouping_key=movement_date.isoformat(),
                        summary=f"Plano sem snapshot aplicável em {movement_date.isoformat()}",
                        criticality="critical",
                        evidence=[{
                            "source_type": "razao_line",
                            "source_id": f"{lote.id}:{index}",
                            "summary": f"Lote {lote.id}, linha {index}",
                        }],
                    )
                elif snapshot_context is None:
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
                else:
                    snapshot_id = snapshot_context.snapshot_id
                    snapshot_accounts = snapshot_context.account_names
                    origin_code = int(normalized["conta_origem"])
                    observed_name = parsed.get("conta_origem_nome")
                    observed_normalized = (
                        _normalize_account_name(observed_name) if observed_name else None
                    )
                    candidates = (
                        snapshot_context.name_candidates.get(observed_normalized, [])
                        if observed_normalized else []
                    )
                    for code in {int(normalized["conta_origem"]), int(normalized["conta_contrapartida"])} - snapshot_context.account_codes - snapshot_context.alias_codes:
                        probable_alias = code == origin_code and len(candidates) == 1
                        _create_razao_review_item(
                            session,
                            review_group_keys,
                            empresa_id=empresa_id,
                            source_type="razao_account_unknown",
                            grouping_key=f"{snapshot_id}:{code}",
                            summary=(
                                f"Possível alias {code} para conta {candidates[0]} no snapshot {snapshot_id}"
                                if probable_alias else f"Conta {code} ausente no snapshot {snapshot_id}"
                            ),
                            criticality="high",
                            evidence=[{
                                "source_type": "razao_line",
                                "source_id": f"{lote.id}:{index}",
                                "summary": (
                                    f"Lote {lote.id}, linha {index}: "
                                    f"'{_safe_account_name(observed_name)}' e "
                                    f"'{_safe_account_name(snapshot_accounts[candidates[0]])}'"
                                    if probable_alias else f"Lote {lote.id}, linha {index}"
                                ),
                            }],
                        )
                    if origin_code in snapshot_accounts and observed_normalized and (
                        observed_normalized
                        != _normalize_account_name(snapshot_accounts[origin_code])
                    ):
                        name_hash = hashlib.sha256(
                            observed_normalized.encode("utf-8")
                        ).hexdigest()[:16]
                        _create_razao_review_item(
                            session,
                            review_group_keys,
                            empresa_id=empresa_id,
                            source_type="razao_semantic_divergence",
                            grouping_key=f"{snapshot_id}:{origin_code}:{name_hash}",
                            summary=f"Descrição da conta {origin_code} diverge do snapshot {snapshot_id}",
                            criticality="critical",
                            evidence=[{
                                "source_type": "razao_line",
                                "source_id": f"{lote.id}:{index}",
                                "summary": (
                                    f"Lote {lote.id}, linha {index}: "
                                    f"'{_safe_account_name(observed_name)}' diverge de "
                                    f"'{_safe_account_name(snapshot_accounts[origin_code])}'"
                                ),
                            }],
                        )

                normalized["historico_normalizado"] = normalize_razao_historico(
                    normalized["historico"]
                )
                models.append(_to_model(lote.id, empresa_id, normalized))
                line_codes = {int(normalized["conta_origem"]), int(normalized["conta_contrapartida"])}
                linkable_codes = (
                    snapshot_context.account_codes
                    if isinstance(snapshot_context, _SnapshotAccountContext)
                    else catalog_codes if not has_company_snapshots else set()
                )
                if line_codes <= linkable_codes and line_codes <= set(account_identities):
                    _update_account_links(
                        account_links,
                        account_identities,
                        session,
                        empresa_id,
                        normalized,
                    )
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
        linhas_processadas = min(block_start + len(block), len(parsed_lancamentos))
        if owns_lote:
            lote.linhas_processadas = linhas_processadas
            lote.total_importadas = imported
            lote.total_invalidas = linhas_processadas - imported
            lote.warnings_total = sum(warning_totals.values())
            lote.warnings_metadata = {"totals_by_code": dict(warning_totals)}
        session.flush()
        if progress is not None:
            progress(
                total_linhas=len(parsed_lancamentos),
                linhas_processadas=linhas_processadas,
                total_importadas=imported,
                total_invalidas=linhas_processadas - imported,
                warnings_total=sum(warning_totals.values()),
            )
        preview_capacity = warning_preview_limit - len(warning_preview)
        if preview_capacity > 0:
            warning_preview.extend(block_warnings[:preview_capacity])

    invalid = len(parsed_lancamentos) - imported
    warnings_total = sum(warning_totals.values())
    if invalid == 0 and warnings_total == 0:
        status = "completed"
    elif imported > 0:
        status = "completed_with_warnings"
    else:
        status = "failed"

    if owns_lote:
        lote.total_importadas = imported
        lote.total_invalidas = invalid
        lote.warnings_total = warnings_total
        lote.warnings_metadata = {"totals_by_code": dict(warning_totals)}
        lote.status = status

    session.flush()
    return ImportacaoRazaoResumo(
        lote_id=lote.id,
        status=status,
        total_linhas=len(parsed_lancamentos),
        total_importadas=imported,
        total_invalidas=invalid,
        warnings=warning_preview,
        warnings_total=warnings_total,
        warnings_metadata={"totals_by_code": dict(warning_totals)},
    )


def _parse_lancamentos_and_validate_company(
    session: Session,
    file_path: str | Path | BinaryIO,
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


def _normalize_account_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    words = re.findall(r"[a-z0-9]+", text)
    return " ".join("banco" if word == "bco" else word for word in words)


def _safe_account_name(value: str) -> str:
    return " ".join("".join(char for char in value if char.isprintable()).split())[:120]


def _create_razao_review_item(
    session: Session,
    group_cache: dict[tuple[str, str], str],
    *,
    empresa_id: int,
    source_type: str,
    grouping_key: str,
    summary: str,
    criticality: str,
    evidence: list[dict[str, str]],
) -> ReviewItem:
    cache_key = (source_type, grouping_key)
    key = group_cache.get(cache_key)
    if key is None:
        key = grouping_key
        while True:
            previous = session.scalar(
                select(ReviewItem).where(
                    ReviewItem.empresa_id == empresa_id,
                    ReviewItem.source_type == source_type,
                    ReviewItem.grouping_key == key,
                ).with_for_update()
            )
            if previous is None or previous.status in {"pending", "in_review"}:
                break
            key = f"{grouping_key}:after:{previous.id}"
        group_cache[cache_key] = key
    return create_review_item(
        session,
        empresa_id=empresa_id,
        source_type=source_type,
        grouping_key=key,
        summary=summary,
        criticality=criticality,
        evidence=evidence,
    )


def _load_snapshot_account_context(
    session: Session, empresa_id: int, snapshot: PlanoContasSnapshot
) -> _SnapshotAccountContext:
    entries = session.scalars(
        select(PlanoContasSnapshotEntry).where(
            PlanoContasSnapshotEntry.snapshot_id == snapshot.id,
            PlanoContasSnapshotEntry.empresa_id == empresa_id,
        )
    ).all()
    account_names = {entry.codigo: entry.nome for entry in entries}
    candidates: dict[str, list[int]] = defaultdict(list)
    for code, name in account_names.items():
        candidates[_normalize_account_name(name)].append(code)
    alias_codes = set(session.scalars(
        select(RazaoAccountAlias.observed_code).where(
            RazaoAccountAlias.snapshot_id == snapshot.id,
            RazaoAccountAlias.empresa_id == empresa_id,
        )
    ).all())
    return _SnapshotAccountContext(
        snapshot_id=snapshot.id,
        account_names=account_names,
        account_codes=set(account_names),
        alias_codes=alias_codes,
        name_candidates=dict(candidates),
    )


def _preload_catalog_accounts(
    session: Session,
    parsed_lancamentos: list[dict[str, Any]],
) -> dict[int, ContaContabil]:
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
        return {}
    accounts = session.scalars(
        select(ContaContabil).where(ContaContabil.codigo.in_(requested))
    ).all()
    return {account.codigo: account for account in accounts}


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


def _ensure_company_account_identities(
    session: Session,
    empresa_id: int,
    catalog_accounts: dict[int, ContaContabil],
) -> dict[int, ContaContabilEmpresa]:
    """Materializa identidades da empresa para os códigos legados válidos."""
    if not catalog_accounts:
        return {}
    existing = session.scalars(
        select(ContaContabilEmpresa).where(
            ContaContabilEmpresa.empresa_id == empresa_id,
            ContaContabilEmpresa.codigo.in_(catalog_accounts),
        )
    ).all()
    identities = {identity.codigo: identity for identity in existing}
    for codigo, account in catalog_accounts.items():
        if codigo in identities:
            continue
        identity = ContaContabilEmpresa(
            empresa_id=empresa_id,
            codigo=codigo,
            classificacao=account.classificacao,
            nome=account.nome,
            tipo=account.tipo,
            grau=account.grau,
            is_active=account.is_active,
            is_financial_origin=account.is_financial_origin,
        )
        session.add(identity)
        identities[codigo] = identity
    session.flush()
    return identities


def _update_account_links(
    account_links: dict[int, EmpresaContaContabil],
    account_identities: dict[int, ContaContabilEmpresa],
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
                conta_contabil_empresa_id=account_identities[conta_codigo].id,
                quantidade_lancamentos=1,
                ultima_utilizacao=data_lancamento,
            )
            account_links[conta_codigo] = vinculo
            session.add(vinculo)
            continue

        vinculo.conta_contabil_empresa_id = account_identities[conta_codigo].id
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
        code = str(warning.get("codigo") or warning_code_from_message(message))
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


def warning_code_from_message(message: str) -> str:
    """Mapeia uma mensagem pública para o código estável compartilhado pela API."""
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


def _file_hash(path: str | Path | BinaryIO) -> str:
    if isinstance(path, (str, Path)):
        content = Path(path).read_bytes()
    else:
        path.seek(0)
        content = path.read()
        path.seek(0)
    digest = hashlib.sha256(content).hexdigest()
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
