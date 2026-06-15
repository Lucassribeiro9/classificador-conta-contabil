import pytest
from openpyxl import Workbook

from core.razao_parser import (
    build_razao_dedup_key,
    RazaoParseError,
    normalize_lancamento_razao,
    normalize_razao_historico,
    parse_razao_xlsx,
)


def _write_workbook(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


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
