from pathlib import Path
from typing import Any

from openpyxl import load_workbook


class RazaoParseError(ValueError):
    """Erro de validacao do arquivo do livro-razao."""


_REQUIRED_COLUMNS = ("data", "historico", "contrapartida", "debito", "credito")
_OPTIONAL_COLUMNS = ("numero",)
_COLUMN_ALIASES = {
    "data": "data",
    "numero": "numero",
    "historico": "historico",
    "contrapartida": "contrapartida",
    "cta.c.part.": "contrapartida",
    "debito": "debito",
    "credito": "credito",
}


def parse_razao_xlsx(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if file_path.suffix.lower() != ".xlsx":
        raise RazaoParseError("Arquivo do razao deve estar no formato .xlsx.")

    workbook = load_workbook(file_path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        conta_origem: str | None = None
        header_by_column: dict[str, int] | None = None
        lancamentos: list[dict[str, Any]] = []

        for row in sheet.iter_rows(values_only=True):
            if _is_empty_row(row):
                continue

            conta_bloco = _extract_account_block(row)
            if conta_bloco is not None:
                conta_origem = conta_bloco
                continue

            maybe_header = _header_by_column(row)
            if maybe_header is not None:
                header_by_column = maybe_header
                continue

            if conta_origem is None or header_by_column is None:
                continue

            if _is_balance_row(row):
                continue

            lancamento = _parse_entry_row(row, conta_origem, header_by_column)
            if lancamento is not None:
                lancamentos.append(lancamento)

        return lancamentos
    finally:
        workbook.close()


def normalize_lancamento_razao(lancamento: dict[str, Any]) -> dict[str, Any]:
    debito = lancamento.get("debito")
    credito = lancamento.get("credito")
    contrapartida = lancamento.get("contrapartida")
    conta_origem = lancamento.get("conta_origem")

    has_debito = not _is_blank_value(debito)
    has_credito = not _is_blank_value(credito)
    if has_debito == has_credito:
        raise RazaoParseError(
            "Linha do razao deve possuir debito ou credito valido."
        )

    if has_debito:
        conta_debito = conta_origem
        conta_credito = contrapartida
        direcao = "debito"
        valor = debito
    else:
        conta_debito = contrapartida
        conta_credito = conta_origem
        direcao = "credito"
        valor = credito

    return {
        "conta_origem": conta_origem,
        "conta_contrapartida": contrapartida,
        "conta_debito": conta_debito,
        "conta_credito": conta_credito,
        "direcao": direcao,
        "data": lancamento.get("data"),
        "numero": lancamento.get("numero"),
        "historico": lancamento.get("historico"),
        "valor": valor,
    }


def normalize_razao_historico(historico: Any) -> str:
    return " ".join(str(historico).strip().lower().split())


def build_razao_dedup_key(lancamento: dict[str, Any]) -> tuple[Any, ...]:
    historico_normalizado = lancamento.get("historico_normalizado")
    if _is_blank_value(historico_normalizado):
        historico_normalizado = normalize_razao_historico(
            lancamento.get("historico", "")
        )

    return (
        lancamento.get("empresa_id"),
        lancamento.get("numero_lancamento"),
        lancamento.get("data"),
        lancamento.get("conta_origem"),
        lancamento.get("conta_contrapartida"),
        lancamento.get("valor"),
        lancamento.get("direcao"),
        historico_normalizado,
    )


def _extract_account_block(row: tuple[Any, ...]) -> str | None:
    for index, value in enumerate(row):
        text = _clean_text(value)
        if not text:
            continue

        normalized = _normalize_text(text)
        if normalized == "conta:" or normalized == "conta":
            return _first_text_after(row, index)

        if normalized.startswith("conta:"):
            account = text.split(":", 1)[1].strip()
            if account:
                return account.split()[0]

    return None


def _first_text_after(row: tuple[Any, ...], index: int) -> str | None:
    for value in row[index + 1 :]:
        text = _clean_text(value)
        if text:
            return text.split()[0]
    return None


def _header_by_column(row: tuple[Any, ...]) -> dict[str, int | None] | None:
    header_by_field: dict[str, int] = {}
    for index, value in enumerate(row):
        field_name = _COLUMN_ALIASES.get(_normalize_text(value))
        if field_name is not None:
            header_by_field[field_name] = index

    if not all(column in header_by_field for column in _REQUIRED_COLUMNS):
        return None

    return {
        field_name: header_by_field.get(field_name)
        for field_name in (*_REQUIRED_COLUMNS, *_OPTIONAL_COLUMNS)
    }


def _parse_entry_row(
    row: tuple[Any, ...],
    conta_origem: str,
    header_by_column: dict[str, int | None],
) -> dict[str, Any] | None:
    data = _cell(row, header_by_column["data"])
    numero = _cell(row, header_by_column["numero"])
    historico = _cell(row, header_by_column["historico"])
    contrapartida = _cell(row, header_by_column["contrapartida"])
    debito = _cell(row, header_by_column["debito"])
    credito = _cell(row, header_by_column["credito"])

    if _is_blank_value(data) or _is_blank_value(historico):
        return None

    return {
        "conta_origem": conta_origem,
        "data": _clean_text(data),
        "numero": _clean_text(numero),
        "historico": _clean_text(historico),
        "contrapartida": _clean_text(contrapartida),
        "debito": debito if not _is_blank_value(debito) else None,
        "credito": credito if not _is_blank_value(credito) else None,
    }


def _cell(row: tuple[Any, ...], index: int | None) -> Any:
    if index is None or index >= len(row):
        return None
    return row[index]


def _is_balance_row(row: tuple[Any, ...]) -> bool:
    return any("saldo anterior" in _normalize_text(value) for value in row)


def _is_empty_row(row: tuple[Any, ...]) -> bool:
    return all(_is_blank_value(value) for value in row)


def _is_blank_value(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _clean_text(value: Any) -> str | None:
    if _is_blank_value(value):
        return None
    return str(value).strip()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .strip()
        .lower()
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("ú", "u")
    )
