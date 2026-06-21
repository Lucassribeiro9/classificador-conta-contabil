from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from core.razao_parser import (
    build_razao_dedup_key,
    RazaoParseError,
    normalize_lancamento_razao,
    normalize_razao_historico,
    parse_razao_xlsx_with_metadata,
    parse_razao_xlsx,
)


def _write_workbook(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_razao_detects_account_blocks_and_ignores_report_noise(tmp_path):
    xlsx_path = tmp_path / "razao.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Livro Razao"],
            [],
            ["Conta:", "10046", "BCO. SANTANDER"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["Saldo anterior", None, None, None, 1000, None],
            [],
            ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None],
            ["Conta:", "20001", "FORNECEDORES"],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["2026-01-03", "43", "Baixa fornecedor", "10046", None, 250.75],
        ],
    )

    lancamentos = parse_razao_xlsx(xlsx_path)

    assert lancamentos == [
        {
            "conta_origem": "10046",
            "data": "2026-01-02",
            "numero": "42",
            "historico": "Pagamento fornecedor",
            "contrapartida": "20001",
            "debito": 250.75,
            "credito": None,
        },
        {
            "conta_origem": "20001",
            "data": "2026-01-03",
            "numero": "43",
            "historico": "Baixa fornecedor",
            "contrapartida": "10046",
            "debito": None,
            "credito": 250.75,
        },
    ]


def test_parse_razao_fixture_sanitizada_representa_layout_real_dominio():
    fixture_path = FIXTURES_DIR / "razao_dominio_layout_sanitizado.xlsx"

    result = parse_razao_xlsx_with_metadata(fixture_path)

    assert result.metadata.empresa_nome == "EMPRESA MODELO LTDA"
    assert result.metadata.cnpj_cpf == "11222333000181"
    assert result.metadata.periodo_inicio == "2024-01-01"
    assert result.metadata.periodo_fim == "2024-12-31"
    assert result.lancamentos == [
        {
            "conta_origem": "10001",
            "data": "2024-01-31",
            "numero": None,
            "historico": "PAGAMENTO FORNECEDOR MODELO",
            "contrapartida": "20951",
            "debito": None,
            "credito": 1256.68,
        },
        {
            "conta_origem": "10001",
            "data": "2024-02-29",
            "numero": None,
            "historico": "RECEBIMENTO CLIENTE MODELO",
            "contrapartida": "10851",
            "debito": 500.00,
            "credito": None,
        },
    ]


def test_parse_razao_fixture_tabular_modelo_com_conta_origem():
    fixture_path = FIXTURES_DIR / "razao_lote_valido.xlsx"

    result = parse_razao_xlsx_with_metadata(fixture_path)

    assert result.metadata.empresa_nome == "EMPRESA TESTE RAZAO LTDA"
    assert result.metadata.cnpj_cpf == "22333444000155"
    assert result.metadata.periodo_inicio == "2024-01-01"
    assert result.metadata.periodo_fim == "2024-12-31"
    assert result.lancamentos == [
        {
            "conta_origem": "10046",
            "data": "2024-01-02",
            "numero": "9001",
            "historico": "ALUGUEL - Lancamento teste 5506",
            "contrapartida": "20102",
            "debito": None,
            "credito": 548.96,
        },
        {
            "conta_origem": "10046",
            "data": "2024-01-03",
            "numero": "9002",
            "historico": "VENDA - Lancamento teste 7912",
            "contrapartida": "30102",
            "debito": 2653.82,
            "credito": None,
        },
        {
            "conta_origem": "10046",
            "data": "2024-01-04",
            "numero": "9003",
            "historico": "IMPOSTO - Lancamento teste 1434",
            "contrapartida": "20104",
            "debito": None,
            "credito": 10131.84,
        },
    ]


def test_parse_razao_normalizes_integer_like_numeric_account_codes(tmp_path):
    xlsx_path = tmp_path / "razao-contas-numericas.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa", "EMPRESA TESTE LTDA"],
            ["CNPJ", "12.345.678/0001-90"],
            ["Periodo inicio", "01/01/2024"],
            ["Periodo fim", "31/12/2024"],
            [],
            ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"],
            ["Conta:", "10046.0", "BANCO TESTE"],
            ["31/01/2024", "142196.0", "PAGAMENTO TESTE", "20001.0", 49.92, None],
        ],
    )

    result = parse_razao_xlsx_with_metadata(xlsx_path)

    assert result.lancamentos == [
        {
            "conta_origem": "10046",
            "data": "2024-01-31",
            "numero": "142196",
            "historico": "PAGAMENTO TESTE",
            "contrapartida": "20001",
            "debito": 49.92,
            "credito": None,
        }
    ]


def test_parse_razao_normalizes_excel_datetime_entry_date(tmp_path):
    xlsx_path = tmp_path / "razao-data-excel.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa", "EMPRESA TESTE LTDA"],
            ["CNPJ", "12.345.678/0001-90"],
            ["Periodo inicio", "01/01/2024"],
            ["Periodo fim", "31/12/2024"],
            [],
            ["Data", "Historico", "Contrapartida", "Debito", "Credito"],
            ["Conta:", "10046", "BANCO TESTE"],
            [datetime(2024, 1, 31), "PAGAMENTO TESTE", "20001", 49.92, None],
        ],
    )

    result = parse_razao_xlsx_with_metadata(xlsx_path)

    assert result.lancamentos[0]["data"] == "2024-01-31"


def test_parse_razao_with_metadata_rejects_unrecognized_layout(tmp_path):
    xlsx_path = tmp_path / "razao-layout-desconhecido.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa", "EMPRESA TESTE LTDA"],
            ["CNPJ", "12.345.678/0001-90"],
            ["Periodo inicio", "01/01/2024"],
            ["Periodo fim", "31/12/2024"],
            [],
            ["Data Movimento", "Descricao", "Valor"],
            ["31/01/2024", "PAGAMENTO TESTE", 100],
        ],
    )

    with pytest.raises(
        RazaoParseError,
        match="Layout do razao nao reconhecido.*cabecalho",
    ):
        parse_razao_xlsx_with_metadata(xlsx_path)


def test_parse_razao_accepts_dominio_export_layout_without_entry_number(tmp_path):
    xlsx_path = tmp_path / "razao-dominio.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa:", None, "EMPRESA TESTE LTDA"],
            ["C.N.P.J.:", None, "12.345.678/0001-90"],
            ["Período:", None, "01/01/2024 - 31/12/2024"],
            [],
            ["RAZÃO"],
            [],
            [
                "Data",
                None,
                "Histórico",
                None,
                None,
                None,
                None,
                "Cta.C.Part.",
                "Débito",
                "Crédito",
                None,
                "Saldo-Exercício",
            ],
            [
                "Conta:",
                10001,
                "1.1.01.01.01.10001",
                None,
                None,
                "CAIXA",
            ],
            [
                None,
                None,
                "SALDO ANTERIOR",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "100D",
            ],
            [
                "2024-01-31",
                None,
                "PAGTO.PRO-LABORE.REF.",
                None,
                None,
                None,
                None,
                20951,
                None,
                1256.68,
                None,
                "1156,68C",
            ],
            [
                "2024-02-01",
                None,
                "SUPRIMENTO DE CAIXA",
                None,
                None,
                None,
                None,
                10046,
                500.00,
                None,
                None,
                "656,68D",
            ],
        ],
    )

    lancamentos = parse_razao_xlsx(xlsx_path)

    assert lancamentos == [
        {
            "conta_origem": "10001",
            "data": "2024-01-31",
            "numero": None,
            "historico": "PAGTO.PRO-LABORE.REF.",
            "contrapartida": "20951",
            "debito": None,
            "credito": 1256.68,
        },
        {
            "conta_origem": "10001",
            "data": "2024-02-01",
            "numero": None,
            "historico": "SUPRIMENTO DE CAIXA",
            "contrapartida": "10046",
            "debito": 500.00,
            "credito": None,
        },
    ]


def test_parse_razao_with_metadata_extracts_company_header(tmp_path):
    xlsx_path = tmp_path / "razao-dominio-metadados.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa:", None, "EMPRESA TESTE LTDA"],
            ["C.N.P.J.:", None, "12.345.678/0001-90"],
            ["Período:", None, "01/01/2024 - 31/12/2024"],
            [],
            [
                "Data",
                None,
                "Histórico",
                None,
                None,
                None,
                None,
                "Cta.C.Part.",
                "Débito",
                "Crédito",
            ],
            ["Conta:", 10001, "1.1.01.01.01.10001", None, None, "CAIXA"],
            [
                "2024-01-31",
                None,
                "PAGTO.PRO-LABORE.REF.",
                None,
                None,
                None,
                None,
                20951,
                None,
                1256.68,
            ],
        ],
    )

    result = parse_razao_xlsx_with_metadata(xlsx_path)

    assert result.metadata.empresa_nome == "EMPRESA TESTE LTDA"
    assert result.metadata.cnpj_cpf == "12345678000190"
    assert result.metadata.periodo_inicio == "2024-01-01"
    assert result.metadata.periodo_fim == "2024-12-31"
    assert not hasattr(result.metadata, "cod_dominio")
    assert result.lancamentos == [
        {
            "conta_origem": "10001",
            "data": "2024-01-31",
            "numero": None,
            "historico": "PAGTO.PRO-LABORE.REF.",
            "contrapartida": "20951",
            "debito": None,
            "credito": 1256.68,
        }
    ]


def test_parse_razao_with_metadata_requires_cnpj_header(tmp_path):
    xlsx_path = tmp_path / "razao-sem-cnpj.xlsx"
    _write_workbook(
        xlsx_path,
        [
            ["Empresa:", None, "EMPRESA TESTE LTDA"],
            ["Período:", None, "01/01/2024 - 31/12/2024"],
            [],
            [
                "Data",
                None,
                "Histórico",
                None,
                None,
                None,
                None,
                "Cta.C.Part.",
                "Débito",
                "Crédito",
            ],
            ["Conta:", 10001, "1.1.01.01.01.10001", None, None, "CAIXA"],
            [
                "2024-01-31",
                None,
                "PAGTO.PRO-LABORE.REF.",
                None,
                None,
                None,
                None,
                20951,
                None,
                1256.68,
            ],
        ],
    )

    with pytest.raises(RazaoParseError, match="cnpj_cpf"):
        parse_razao_xlsx_with_metadata(xlsx_path)


def test_parse_razao_rejects_non_xlsx_files(tmp_path):
    csv_path = tmp_path / "razao.csv"
    csv_path.write_text("Conta:,10046\n", encoding="utf-8")

    with pytest.raises(RazaoParseError, match="xlsx"):
        parse_razao_xlsx(csv_path)


def test_normalize_razao_debit_line_uses_block_account_as_debit_side():
    lancamento = normalize_lancamento_razao(
        {
            "conta_origem": "10046",
            "data": "2026-01-02",
            "numero": "42",
            "historico": "Pagamento fornecedor",
            "contrapartida": "20001",
            "debito": 250.75,
            "credito": None,
        }
    )

    assert lancamento == {
        "conta_origem": "10046",
        "conta_contrapartida": "20001",
        "conta_debito": "10046",
        "conta_credito": "20001",
        "direcao": "debito",
        "data": "2026-01-02",
        "numero": "42",
        "historico": "Pagamento fornecedor",
        "valor": 250.75,
    }


def test_normalize_razao_credit_line_uses_counterpart_as_debit_side():
    lancamento = normalize_lancamento_razao(
        {
            "conta_origem": "20001",
            "data": "2026-01-03",
            "numero": "43",
            "historico": "Baixa fornecedor",
            "contrapartida": "10046",
            "debito": None,
            "credito": 250.75,
        }
    )

    assert lancamento == {
        "conta_origem": "20001",
        "conta_contrapartida": "10046",
        "conta_debito": "10046",
        "conta_credito": "20001",
        "direcao": "credito",
        "data": "2026-01-03",
        "numero": "43",
        "historico": "Baixa fornecedor",
        "valor": 250.75,
    }


def test_normalize_razao_line_without_debit_or_credit_raises_clear_error():
    with pytest.raises(RazaoParseError, match="debito ou credito"):
        normalize_lancamento_razao(
            {
                "conta_origem": "10046",
                "data": "2026-01-04",
                "numero": "44",
                "historico": "Lancamento sem valor",
                "contrapartida": "20001",
                "debito": None,
                "credito": None,
            }
        )


def test_normalize_razao_line_with_debit_and_credit_raises_clear_error():
    with pytest.raises(RazaoParseError, match="debito ou credito"):
        normalize_lancamento_razao(
            {
                "conta_origem": "10046",
                "data": "2026-01-04",
                "numero": None,
                "historico": "Lancamento com dois valores",
                "contrapartida": "20001",
                "debito": 10.00,
                "credito": 10.00,
            }
        )


def test_normalize_razao_historico_is_stable_for_case_and_extra_spaces():
    assert (
        normalize_razao_historico("  Pagamento   FORNECEDOR  ")
        == "pagamento fornecedor"
    )


def test_build_razao_dedup_key_is_stable_for_equivalent_history_text():
    base_lancamento = {
        "empresa_id": 7,
        "numero_lancamento": "42",
        "data": "2026-01-02",
        "conta_origem": "10046",
        "conta_contrapartida": "20001",
        "valor": 250.75,
        "direcao": "debito",
        "historico": "Pagamento fornecedor",
    }
    equivalent_lancamento = {
        **base_lancamento,
        "historico": "  PAGAMENTO   fornecedor  ",
    }

    assert build_razao_dedup_key(base_lancamento) == build_razao_dedup_key(
        equivalent_lancamento
    )


@pytest.mark.parametrize(
    "changed_fields",
    [
        {"empresa_id": 8},
        {"numero_lancamento": "43"},
        {"data": "2026-01-03"},
        {"valor": 300.00},
        {"direcao": "credito"},
        {"conta_origem": "10047"},
        {"conta_contrapartida": "20002"},
    ],
)
def test_build_razao_dedup_key_changes_for_composite_key_fields(changed_fields):
    base_lancamento = {
        "empresa_id": 7,
        "numero_lancamento": "42",
        "data": "2026-01-02",
        "conta_origem": "10046",
        "conta_contrapartida": "20001",
        "valor": 250.75,
        "direcao": "debito",
        "historico": "Pagamento fornecedor",
    }
    changed_lancamento = {**base_lancamento, **changed_fields}

    assert build_razao_dedup_key(base_lancamento) != build_razao_dedup_key(
        changed_lancamento
    )
