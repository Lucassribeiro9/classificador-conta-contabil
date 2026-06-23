from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import (
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
)
from core.movimentos_operacionais_parser import parse_movimentos_operacionais_xlsx


@dataclass(frozen=True)
class ImportacaoMovimentoOperacionalResumo:
    """Resumo operacional retornado apos processar um arquivo."""

    lote_id: int
    status: str
    total_linhas: int
    total_importadas: int
    total_invalidas: int
    warnings: list[dict[str, Any]]


@dataclass(frozen=True)
class _LinhaValidada:
    """Resultado interno da validacao de uma linha operacional."""

    status: str
    is_valid: bool
    warnings: list[str]
    movimento: dict[str, Any]


class MovimentoOperacionalImportError(ValueError):
    """Erro de validacao da importacao operacional."""


def import_movimentos_operacionais(
    session: Session,
    path: str | Path,
    *,
    empresa_id: int,
    usuario_id: int,
    original_filename: str,
) -> ImportacaoMovimentoOperacionalResumo:
    """Importa planilha operacional, criando lote e movimentos revisaveis."""

    file_path = Path(path)
    file_hash = _file_hash(file_path)
    _ensure_file_hash_not_successfully_imported(session, empresa_id, file_hash)

    parsed = parse_movimentos_operacionais_xlsx(file_path)
    empresa = _ensure_file_company_matches_target(
        session,
        empresa_id,
        parsed.metadata.cnpj_cpf,
    )
    periodo_inicio = date.fromisoformat(parsed.metadata.periodo_inicio)
    periodo_fim = date.fromisoformat(parsed.metadata.periodo_fim)
    contas_por_codigo = _load_contas_por_codigo(session)
    contas_vinculadas = _load_contas_vinculadas(session, empresa_id)
    warnings = _metadata_warnings(empresa, parsed.metadata.codigo_dominio)
    imported = 0

    lote = LoteImportacaoMovimentoOperacional(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        original_filename=original_filename,
        file_hash=file_hash,
        status="processing",
        total_linhas=len(parsed.movimentos),
        total_importadas=0,
        total_invalidas=0,
        warnings_metadata={"warnings": []},
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        cnpj_cpf_arquivo=parsed.metadata.cnpj_cpf,
        codigo_dominio_arquivo=parsed.metadata.codigo_dominio or None,
    )
    session.add(lote)
    session.flush()

    for index, movimento in enumerate(parsed.movimentos, start=1):
        validation = _validar_movimento(
            movimento,
            contas_por_codigo=contas_por_codigo,
            contas_vinculadas=contas_vinculadas,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
        )
        if validation.warnings:
            warnings.append({"linha": index, "warnings": validation.warnings})
        if not validation.is_valid:
            continue

        session.add(_to_model(lote.id, empresa_id, validation))
        imported += 1

    invalid = len(parsed.movimentos) - imported
    lote.total_importadas = imported
    lote.total_invalidas = invalid
    lote.warnings_metadata = {"warnings": warnings}
    if not warnings:
        lote.status = "completed"
    elif imported > 0:
        lote.status = "completed_with_warnings"
    else:
        lote.status = "failed"

    session.flush()
    return ImportacaoMovimentoOperacionalResumo(
        lote_id=lote.id,
        status=lote.status,
        total_linhas=lote.total_linhas,
        total_importadas=lote.total_importadas,
        total_invalidas=lote.total_invalidas,
        warnings=warnings,
    )


def _ensure_file_company_matches_target(
    session: Session,
    empresa_id: int,
    file_cnpj_cpf: str,
) -> Empresa:
    """Garante que a planilha pertence a empresa selecionada."""

    empresa = session.get(Empresa, empresa_id)
    if empresa is None:
        raise MovimentoOperacionalImportError("Empresa da importacao nao encontrada.")
    if not empresa.is_active:
        raise MovimentoOperacionalImportError(
            "Empresa da importacao esta inativa; reative a empresa antes de importar."
        )
    if file_cnpj_cpf != empresa.cnpj_cpf:
        raise MovimentoOperacionalImportError(
            "CNPJ da planilha operacional nao corresponde a empresa selecionada."
        )
    return empresa


def _metadata_warnings(
    empresa: Empresa,
    codigo_dominio_arquivo: str,
) -> list[dict[str, Any]]:
    """Retorna warnings de metadados que nao bloqueiam o lote."""

    if codigo_dominio_arquivo and codigo_dominio_arquivo != str(empresa.cod_dominio):
        return [
            {
                "linha": None,
                "warnings": [
                    "Codigo dominio do arquivo diverge da empresa selecionada."
                ],
            }
        ]
    return []


def _validar_movimento(
    movimento: Mapping[str, Any],
    *,
    contas_por_codigo: Mapping[int, ContaContabil],
    contas_vinculadas: set[int],
    periodo_inicio: date,
    periodo_fim: date,
) -> _LinhaValidada:
    """Valida uma linha e deriva campos para persistencia."""

    data = _parse_date(movimento.get("data"))
    conta_financeira = _parse_account_code(movimento.get("conta_financeira"))
    historico = _clean_text(movimento.get("historico"))
    valor_original = _parse_decimal(movimento.get("valor"))
    contrapartida = _parse_account_code(movimento.get("contrapartida"))
    tipo_movimento = _clean_text(movimento.get("tipo_movimento"))
    invalid_warnings = _invalid_warnings(
        data=data,
        conta_financeira=conta_financeira,
        historico=historico,
        valor_original=valor_original,
        contrapartida=contrapartida,
        contas_por_codigo=contas_por_codigo,
    )
    if invalid_warnings:
        return _LinhaValidada(
            status="invalida",
            is_valid=False,
            warnings=invalid_warnings,
            movimento={},
        )

    assert data is not None
    assert conta_financeira is not None
    assert historico is not None
    assert valor_original is not None

    line_warnings = _line_warnings(
        data=data,
        conta_financeira=conta_financeira,
        contrapartida=contrapartida,
        valor_original=valor_original,
        tipo_movimento=tipo_movimento,
        contas_vinculadas=contas_vinculadas,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
    )
    status = _resolve_status(line_warnings, contrapartida)

    return _LinhaValidada(
        status=status,
        is_valid=True,
        warnings=line_warnings,
        movimento={
            "data": data,
            "conta_financeira": conta_financeira,
            "historico": historico,
            "historico_normalizado": _normalize_historico(historico),
            "valor_original": valor_original,
            "valor_absoluto": abs(valor_original),
            "direcao": "entrada" if valor_original > 0 else "saida",
            "tipo_movimento": tipo_movimento,
            "documento": _clean_text(movimento.get("documento")),
            "observacao": _clean_text(movimento.get("observacao")),
            "contrapartida_informada": contrapartida,
        },
    )


def _invalid_warnings(
    *,
    data: date | None,
    conta_financeira: int | None,
    historico: str | None,
    valor_original: Decimal | None,
    contrapartida: int | None,
    contas_por_codigo: Mapping[int, ContaContabil],
) -> list[str]:
    """Monta mensagens de bloqueio para linha invalida."""

    warnings: list[str] = []
    if data is None:
        warnings.append("Data do movimento ausente ou invalida.")
    if conta_financeira is None:
        warnings.append("Conta financeira ausente.")
    if historico is None:
        warnings.append("Historico ausente.")
    if valor_original is None or valor_original == 0:
        warnings.append("Valor do movimento ausente, invalido ou zero.")
    if conta_financeira is not None and not _is_classificavel(
        contas_por_codigo.get(conta_financeira)
    ):
        warnings.append(
            f"Conta financeira {conta_financeira} inexistente, sintetica ou inativa."
        )
    if contrapartida is not None and not _is_classificavel(
        contas_por_codigo.get(contrapartida)
    ):
        warnings.append(
            f"Contrapartida {contrapartida} inexistente, sintetica ou inativa."
        )
    return warnings


def _line_warnings(
    *,
    data: date,
    conta_financeira: int,
    contrapartida: int | None,
    valor_original: Decimal,
    tipo_movimento: str | None,
    contas_vinculadas: set[int],
    periodo_inicio: date,
    periodo_fim: date,
) -> list[str]:
    """Monta warnings recuperaveis de uma linha valida."""

    warnings: list[str] = []
    if data < periodo_inicio or data > periodo_fim:
        warnings.append("Data do movimento fora do periodo do lote.")
    if conta_financeira not in contas_vinculadas:
        warnings.append(f"Conta financeira {conta_financeira} nao vinculada a empresa.")
    if contrapartida is not None and contrapartida not in contas_vinculadas:
        warnings.append(f"Contrapartida {contrapartida} nao vinculada a empresa.")
    if tipo_movimento == "entrada" and valor_original < 0:
        warnings.append("Tipo de movimento incoerente com o sinal do valor.")
    if tipo_movimento == "saida" and valor_original > 0:
        warnings.append("Tipo de movimento incoerente com o sinal do valor.")
    if tipo_movimento in {"transferencia", "aplicacao", "resgate"}:
        if contrapartida is None:
            warnings.append(f"Tipo de movimento {tipo_movimento} exige contrapartida.")
    return warnings


def _resolve_status(warnings: list[str], contrapartida: int | None) -> str:
    """Resolve status inicial do movimento persistido."""

    if warnings:
        return "revisao"
    if contrapartida is None:
        return "pendente"
    return "pre_classificado"


def _to_model(
    lote_id: int,
    empresa_id: int,
    validation: _LinhaValidada,
) -> MovimentoOperacionalImportado:
    """Converte linha validada para modelo ORM."""

    movimento = validation.movimento
    return MovimentoOperacionalImportado(
        lote_id=lote_id,
        empresa_id=empresa_id,
        data=movimento["data"],
        conta_financeira=movimento["conta_financeira"],
        historico=movimento["historico"],
        historico_normalizado=movimento["historico_normalizado"],
        valor_original=movimento["valor_original"],
        valor_absoluto=movimento["valor_absoluto"],
        direcao=movimento["direcao"],
        tipo_movimento=movimento["tipo_movimento"],
        documento=movimento["documento"],
        observacao=movimento["observacao"],
        contrapartida_informada=movimento["contrapartida_informada"],
        contrapartida_sugerida=None,
        contrapartida_final=None,
        confidence_sugerida=None,
        status=validation.status,
        elegivel_treino=False,
        mensagens_validacao=validation.warnings,
        conta_debito=None,
        conta_credito=None,
    )


def _load_contas_por_codigo(session: Session) -> dict[int, ContaContabil]:
    """Carrega catalogo contabil por codigo reduzido."""

    contas = session.execute(select(ContaContabil)).scalars().all()
    return {conta.codigo: conta for conta in contas}


def _load_contas_vinculadas(session: Session, empresa_id: int) -> set[int]:
    """Carrega codigos de contas ja vinculadas a empresa."""

    rows = session.execute(
        select(EmpresaContaContabil.conta_codigo).where(
            EmpresaContaContabil.empresa_id == empresa_id
        )
    ).all()
    return {row[0] for row in rows}


def _ensure_file_hash_not_successfully_imported(
    session: Session,
    empresa_id: int,
    file_hash: str,
) -> None:
    """Bloqueia reimportacao de arquivo ja concluido total ou parcialmente."""

    existing_lote = session.execute(
        select(LoteImportacaoMovimentoOperacional).where(
            LoteImportacaoMovimentoOperacional.empresa_id == empresa_id,
            LoteImportacaoMovimentoOperacional.file_hash == file_hash,
            LoteImportacaoMovimentoOperacional.status.in_(
                ["completed", "completed_with_warnings"]
            ),
        )
    ).scalar_one_or_none()
    if existing_lote is not None:
        raise MovimentoOperacionalImportError(
            "Arquivo ja importado com sucesso para esta empresa."
        )


def _file_hash(path: Path) -> str:
    """Calcula hash sha256 do arquivo importado."""

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _is_classificavel(conta: ContaContabil | None) -> bool:
    """Indica se conta pode ser usada em movimento operacional."""

    if conta is None:
        return False
    return conta.is_classificavel


def _parse_account_code(value: Any) -> int | None:
    """Converte codigo de conta em inteiro."""

    if _is_blank(value):
        return None
    try:
        return int(Decimal(str(value).strip()))
    except (InvalidOperation, ValueError):
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    """Converte valor para Decimal."""

    if _is_blank(value):
        return None
    try:
        return Decimal(str(value).strip())
    except InvalidOperation:
        return None


def _parse_date(value: Any) -> date | None:
    """Converte datas ISO, brasileiras ou Excel para date."""

    if _is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    for separator, order in (("-", "ymd"), ("/", "dmy")):
        if separator not in text:
            continue
        parts = text.split(separator)
        if len(parts) != 3:
            continue
        try:
            if order == "ymd":
                year, month, day = parts
            else:
                day, month, year = parts
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def _normalize_historico(historico: str) -> str:
    """Normaliza historico para consultas e classificacao futura."""

    return " ".join(historico.strip().lower().split())


def _clean_text(value: Any) -> str | None:
    """Retorna texto limpo ou None para vazio."""

    if _is_blank(value):
        return None
    return str(value).strip()


def _is_blank(value: Any) -> bool:
    """Indica se valor deve ser tratado como vazio."""

    return value is None or str(value).strip() == ""
