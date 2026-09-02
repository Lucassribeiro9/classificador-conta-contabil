from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/movimentos-operacionais-planilha-modelo.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def normalized_doc() -> str:
    return " ".join(read_doc().lower().split())


def test_documento_movimentos_referencia_spec_e_modelos_oficiais():
    doc = read_doc()

    assert "docs/specs/08-movimentos-operacionais-classificacao.md" in doc
    expected_paths = (
        "tests/fixtures/modelo_movimentos_operacionais_valor_saldo.xlsx",
        "tests/fixtures/modelo_movimentos_operacionais_debito_credito_saldo.xlsx",
        "tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx",
    )

    for expected_path in expected_paths:
        assert expected_path in doc


def test_documento_explica_quando_usar_cada_layout():
    doc = normalized_doc()

    required_content = (
        "quando usar o layout a",
        "valor assinado",
        "valor positivo representa entrada",
        "valor negativo representa saida",
        "quando usar o layout b",
        "credito representa entrada",
        "debito representa saida",
        "exatamente uma",
        "modelo legado",
        "sem saldo",
    )

    for content in required_content:
        assert content in doc


def test_documento_explica_campos_operacionais_e_colunas_do_sistema():
    doc = normalized_doc()

    required_content = (
        "conta_financeira",
        "contrapartida",
        "tipo_movimento",
        "documento",
        "observacao",
        "status_sugerido",
        "confidence_sugerida",
        "mensagem_validacao",
        "preenchidas pelo sistema",
    )

    for content in required_content:
        assert content in doc


def test_documento_explica_saldo_warnings_revisao_e_razao():
    doc = normalized_doc()

    required_content = (
        "saldo observado",
        "saldo calculado",
        "saldo ajuda conferencia",
        "nao classificacao",
        "warnings",
        "completed_with_warnings",
        "revisao",
        "pendente",
        "pre_classificado",
        "razao canonico",
        "nao vira razao automaticamente",
    )

    for content in required_content:
        assert content in doc


def test_documento_lista_erros_comuns_e_evidencias_seguras():
    doc = normalized_doc()

    required_content = (
        "erros e warnings comuns",
        "cnpj/cpf divergente",
        "layout ambiguo",
        "debito e credito preenchidos",
        "saldo ausente",
        "saldo divergente",
        "nao use dados reais",
        "nao anexe planilhas de cliente",
    )

    for content in required_content:
        assert content in doc
