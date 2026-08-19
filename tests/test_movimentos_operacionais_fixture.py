from pathlib import Path

from openpyxl import load_workbook


LEGACY_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "modelo_movimentos_operacionais_classificacao.xlsx"
)
VALOR_SALDO_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "modelo_movimentos_operacionais_valor_saldo.xlsx"
)
DEBITO_CREDITO_SALDO_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "modelo_movimentos_operacionais_debito_credito_saldo.xlsx"
)

EXPECTED_SHEETS = ["Movimentos", "Instrucoes", "Exemplos"]
METADATA_LABELS = {
    "Empresa",
    "Codigo dominio",
    "CNPJ/CPF",
    "Periodo inicio",
    "Periodo fim",
}
LEGACY_HEADERS = [
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
VALOR_SALDO_HEADERS = [
    "data",
    "conta_financeira",
    "historico",
    "valor",
    "saldo",
    "contrapartida",
    "tipo_movimento",
    "documento",
    "observacao",
    "status_sugerido",
    "confidence_sugerida",
    "mensagem_validacao",
]
DEBITO_CREDITO_SALDO_HEADERS = [
    "data",
    "conta_financeira",
    "historico",
    "debito",
    "credito",
    "saldo",
    "contrapartida",
    "tipo_movimento",
    "documento",
    "observacao",
    "status_sugerido",
    "confidence_sugerida",
    "mensagem_validacao",
]

MODEL_FIXTURES = [
    (LEGACY_FIXTURE_PATH, LEGACY_HEADERS),
    (VALOR_SALDO_FIXTURE_PATH, VALOR_SALDO_HEADERS),
    (DEBITO_CREDITO_SALDO_FIXTURE_PATH, DEBITO_CREDITO_SALDO_HEADERS),
]


def _find_header_row(sheet):
    required = {"data", "conta_financeira", "historico"}
    for row in sheet.iter_rows(values_only=True):
        values = [str(cell).strip() if cell is not None else "" for cell in row]
        if required.issubset(values):
            return values
    return None


def _metadata_labels(sheet):
    return {
        str(row[0]).strip()
        for row in sheet.iter_rows(min_row=1, max_row=8, values_only=True)
        if row and row[0] is not None
    }


def test_modelos_movimentos_operacionais_estao_versionados():
    for fixture_path, _headers in MODEL_FIXTURES:
        assert fixture_path.exists(), f"Fixture ausente: {fixture_path.name}"


def test_modelos_movimentos_operacionais_definem_contratos_de_headers():
    for fixture_path, expected_headers in MODEL_FIXTURES:
        workbook = load_workbook(fixture_path, read_only=True, data_only=True)
        try:
            assert workbook.sheetnames == EXPECTED_SHEETS

            sheet = workbook["Movimentos"]
            assert METADATA_LABELS.issubset(_metadata_labels(sheet))

            headers = _find_header_row(sheet)
            assert headers == expected_headers
        finally:
            workbook.close()


def test_modelos_movimentos_operacionais_nao_trazem_dados_reais():
    forbidden_fragments = {
        "empresa brasileira de beneficios",
        "pagto instituicao",
        "lucas",
        "ribeiro",
        "dominio contabilidade",
    }

    for fixture_path, _headers in MODEL_FIXTURES:
        workbook = load_workbook(fixture_path, read_only=True, data_only=True)
        try:
            sheet = workbook["Movimentos"]

            assert sheet["B2"].value is None
            assert sheet["B3"].value is None
            assert sheet["B4"].value is None
            assert sheet["B5"].value is None
            assert sheet["B6"].value is None

            for row in sheet.iter_rows(values_only=True):
                for value in row:
                    if value is None:
                        continue
                    normalized = str(value).strip().lower()
                    assert all(
                        fragment not in normalized for fragment in forbidden_fragments
                    )
        finally:
            workbook.close()


def test_modelos_movimentos_operacionais_trazem_exemplos_ficticios():
    for fixture_path in [VALOR_SALDO_FIXTURE_PATH, DEBITO_CREDITO_SALDO_FIXTURE_PATH]:
        workbook = load_workbook(fixture_path, read_only=True, data_only=True)
        try:
            sheet = workbook["Exemplos"]

            rows = list(sheet.iter_rows(values_only=True))
            assert any(
                "exemplo" in str(cell).lower()
                for row in rows
                for cell in row
                if cell
            )
            assert any(
                "saldo" in str(cell).lower()
                for row in rows
                for cell in row
                if cell
            )
        finally:
            workbook.close()


def test_modelo_legado_movimentos_operacionais_permanece_sem_saldo():
    workbook = load_workbook(LEGACY_FIXTURE_PATH, read_only=True, data_only=True)
    try:
        assert workbook.sheetnames == EXPECTED_SHEETS

        sheet = workbook["Movimentos"]
        assert METADATA_LABELS.issubset(_metadata_labels(sheet))

        headers = _find_header_row(sheet)
        assert headers == LEGACY_HEADERS
        assert "saldo" not in headers

    finally:
        workbook.close()
