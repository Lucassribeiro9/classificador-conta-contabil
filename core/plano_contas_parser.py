from pathlib import Path
from typing import Any

from openpyxl import load_workbook


class PlanoContasParseError(ValueError):
    """Erro de validacao do arquivo de plano de contas."""


_REQUIRED_COLUMNS = {
    "codigo": "codigo",
    "tipo": "tipo",
    "classificacao": "classificacao",
    "nome": "nome",
    "grau": "grau",
}


def parse_plano_contas_xlsx(path: str | Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=False, data_only=True)
    try:
        sheet = workbook.active

        header_by_column = _find_header_by_column(sheet.iter_rows(values_only=True))
        merged_values_by_cell = _merged_values_by_cell(sheet, header_by_column)
        contas: list[dict[str, Any]] = []

        for row_number, row in enumerate(
            sheet.iter_rows(
                min_row=header_by_column["row_number"] + 1,
                values_only=True,
            ),
            start=header_by_column["row_number"] + 1,
        ):
            if _is_empty_row(row) or _is_system_footer_row(
                row_number, row, sheet
            ):
                continue
            contas.append(
                _parse_account_row(
                    row_number, row, header_by_column, merged_values_by_cell
                )
            )

        return contas
    finally:
        workbook.close()


def _find_header_by_column(rows) -> dict[str, int]:
    for row_number, row in enumerate(rows, start=1):
        normalized_cells = {
            _normalize_header(value): index
            for index, value in enumerate(row)
            if _normalize_header(value)
        }
        if "tipo" not in normalized_cells and "t" in normalized_cells:
            normalized_cells["tipo"] = normalized_cells["t"]
        if all(column in normalized_cells for column in _REQUIRED_COLUMNS):
            return {
                "row_number": row_number,
                **{
                    field_name: normalized_cells[column_name]
                    for column_name, field_name in _REQUIRED_COLUMNS.items()
                },
            }

    raise PlanoContasParseError(
        "Cabecalho do plano de contas nao encontrado: "
        "esperado Codigo, Tipo, Classificacao, Nome e Grau."
    )


def _parse_account_row(
    row_number: int,
    row: tuple[Any, ...],
    header_by_column: dict[str, int],
    merged_values_by_cell: dict[tuple[int, int], Any],
) -> dict[str, Any]:
    raw_account = {
        field: _cell(row, column_index, merged_values_by_cell, row_number)
        for field, column_index in header_by_column.items()
        if field != "row_number"
    }
    missing_fields = [
        field for field, value in raw_account.items() if _is_blank_value(value)
    ]
    if missing_fields:
        raise PlanoContasParseError(
            f"Linha {row_number} incompleta: campos ausentes "
            f"{', '.join(sorted(missing_fields))}."
        )

    tipo = str(raw_account["tipo"]).strip().upper()
    if tipo not in {"A", "S"}:
        raise PlanoContasParseError(
            f"Linha {row_number} invalida: tipo deve ser A ou S."
        )

    try:
        codigo = int(raw_account["codigo"])
        grau = int(raw_account["grau"])
    except (TypeError, ValueError) as exc:
        raise PlanoContasParseError(
            f"Linha {row_number} invalida: codigo e grau devem ser numericos."
        ) from exc

    return {
        "codigo": codigo,
        "tipo": tipo,
        "classificacao": str(raw_account["classificacao"]).strip(),
        "nome": str(raw_account["nome"]).strip(),
        "grau": grau,
    }


def _merged_values_by_cell(
    sheet, header_by_column: dict[str, int]
) -> dict[tuple[int, int], Any]:
    column_indexes = {
        index for field, index in header_by_column.items() if field != "row_number"
    }
    values: dict[tuple[int, int], Any] = {}
    first_data_row = header_by_column["row_number"] + 1

    for merged_range in sheet.merged_cells.ranges:
        anchor_value = sheet.cell(
            row=merged_range.min_row, column=merged_range.min_col
        ).value
        for index in column_indexes:
            column = index + 1
            if merged_range.min_col <= column <= merged_range.max_col:
                for row_number in range(
                    max(first_data_row, merged_range.min_row),
                    merged_range.max_row + 1,
                ):
                    values[(row_number, index)] = anchor_value

    return values


def _cell(
    row: tuple[Any, ...],
    index: int,
    merged_values_by_cell: dict[tuple[int, int], Any],
    row_number: int,
) -> Any:
    if index >= len(row):
        return None

    value = row[index]
    if not _is_blank_value(value):
        return value
    return merged_values_by_cell.get((row_number, index))


def _is_system_footer_row(row_number: int, row: tuple[Any, ...], sheet) -> bool:
    populated_indexes = [
        index for index, value in enumerate(row) if not _is_blank_value(value)
    ]
    if len(populated_indexes) != 1:
        return False

    index = populated_indexes[0]
    value = row[index]
    if not isinstance(value, str):
        return False

    coordinate = sheet.cell(row=row_number, column=index + 1).coordinate
    return any(
        coordinate in merged_range and merged_range.max_col > merged_range.min_col
        for merged_range in sheet.merged_cells.ranges
    )


def _is_empty_row(row: tuple[Any, ...]) -> bool:
    return all(_is_blank_value(value) for value in row)


def _is_blank_value(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _normalize_header(value: Any) -> str:
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
