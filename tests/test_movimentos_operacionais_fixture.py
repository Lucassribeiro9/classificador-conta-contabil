from pathlib import Path

from openpyxl import load_workbook


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "modelo_movimentos_operacionais_classificacao.xlsx"
)


def _find_header_row(sheet):
    required = {"data", "conta_financeira", "historico", "valor"}
    for row in sheet.iter_rows(values_only=True):
        values = [str(cell).strip() if cell is not None else "" for cell in row]
        if required.issubset(values):
            return values
    return None


def test_modelo_movimentos_operacionais_fixture_esta_versionada():
    assert FIXTURE_PATH.exists()


def test_modelo_movimentos_operacionais_fixture_define_contrato_base():
    workbook = load_workbook(FIXTURE_PATH, read_only=True, data_only=True)
    try:
        assert workbook.sheetnames == ["Movimentos", "Instrucoes", "Exemplos"]

        sheet = workbook["Movimentos"]
        metadata_labels = {
            str(row[0]).strip()
            for row in sheet.iter_rows(min_row=1, max_row=8, values_only=True)
            if row and row[0] is not None
        }
        assert {
            "Empresa",
            "Codigo dominio",
            "CNPJ/CPF",
            "Periodo inicio",
            "Periodo fim",
        }.issubset(metadata_labels)

        headers = _find_header_row(sheet)
        assert headers == [
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
            "status_sugerido",
            "confidence_sugerida",
            "mensagem_validacao",
        ]
    finally:
        workbook.close()


def test_modelo_movimentos_operacionais_fixture_nao_traz_identificacao_real():
    workbook = load_workbook(FIXTURE_PATH, read_only=True, data_only=True)
    try:
        sheet = workbook["Movimentos"]

        assert sheet["B2"].value is None
        assert sheet["B3"].value is None
        assert sheet["B4"].value is None
        assert sheet["B5"].value is None
        assert sheet["B6"].value is None
    finally:
        workbook.close()
