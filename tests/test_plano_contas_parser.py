import pytest
from openpyxl import Workbook

from core.plano_contas_parser import PlanoContasParseError, parse_plano_contas_xlsx


def _write_workbook(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_parse_plano_contas_ignores_report_header_empty_rows_and_normalizes_accounts(
    tmp_path,
):
    xlsx_path = tmp_path / "plano-contas.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Relatorio do Plano de Contas"],
            ["Empresa Modelo"],
            [],
            ["Codigo", "Tipo", "Classificacao", "Nome", "Grau"],
            [],
            [1000, "S", "1", "ATIVO", 1],
            [10046, "A", "1.1.01.01.02.10046", "BCO. SANTANDER", 6],
        ],
    )

    contas = parse_plano_contas_xlsx(xlsx_path)

    assert contas == [
        {
            "codigo": 1000,
            "tipo": "S",
            "classificacao": "1",
            "nome": "ATIVO",
            "grau": 1,
        },
        {
            "codigo": 10046,
            "tipo": "A",
            "classificacao": "1.1.01.01.02.10046",
            "nome": "BCO. SANTANDER",
            "grau": 6,
        },
    ]


def test_parse_plano_contas_reports_incomplete_rows_with_clear_message(tmp_path):
    xlsx_path = tmp_path / "plano-contas-incompleto.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Codigo", "Tipo", "Classificacao", "Nome", "Grau"],
            [10046, "A", "1.1.01.01.02.10046", None, 6],
        ],
    )

    with pytest.raises(PlanoContasParseError, match="Linha 2.*nome"):
        parse_plano_contas_xlsx(xlsx_path)
