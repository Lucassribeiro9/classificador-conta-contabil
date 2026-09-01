from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROTEIRO = ROOT / "docs/homologacao/roundtrip-planilha-classificada.md"
ROTEIRO_OPERADOR = ROOT / "docs/homologacao-roteiro-operador-contador.md"


def read_roteiro() -> str:
    return ROTEIRO.read_text(encoding="utf-8")


def normalized_roteiro() -> str:
    return " ".join(read_roteiro().lower().split())


def test_roteiro_roundtrip_existe_e_referencia_contexto_canonico():
    roteiro = read_roteiro()

    assert "# Roteiro de Homologacao do Round-trip da Planilha Classificada" in roteiro
    assert "docs/specs/16-planilha-classificada-feedback-roundtrip.md" in roteiro
    assert "#362" in roteiro
    assert "#417" in roteiro
    assert "#429" in roteiro
    assert "#351" in roteiro


def test_roteiro_roundtrip_documenta_rotas_campos_e_estados():
    roteiro = normalized_roteiro()

    required_content = (
        "get `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada`",
        "post `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada/feedback`",
        "`decisao_revisao`",
        "`contrapartida_final`",
        "`observacao_revisao`",
        "`contrapartida`",
        "`row_version`",
        "`export_revision`",
        "`x-service-credential`",
        "`jwt`",
        "`aplicada`",
        "`ignorada`",
        "`invalida`",
        "`conflitante`",
        "`nao_autorizada`",
    )

    for content in required_content:
        assert content in roteiro


def test_roteiro_roundtrip_define_fluxos_reproduziveis_e_evidencias_seguras():
    roteiro = normalized_roteiro()

    required_content = (
        "download",
        "edicao permitida",
        "reenvio",
        "aprovacao",
        "correcao",
        "rejeicao",
        "processamento parcial",
        "reenvio idempotente",
        "planilha antiga",
        "layouts a/b",
        "nao anexe a planilha inteira",
        "nao registre senhas, tokens, segredos",
    )

    for content in required_content:
        assert content in roteiro


def test_roteiro_roundtrip_inclui_checklist_preenchivel():
    roteiro = read_roteiro()

    required_content = (
        "| Etapa | Status | Evidencia tratada | Observacoes |",
        "Resultado final: APROVADO / REPROVADO / BLOQUEADO",
        "Responsavel pela execucao:",
        "Commit testado:",
        "Ambiente:",
    )

    for content in required_content:
        assert content in roteiro


def test_roteiro_operador_referencia_roundtrip_como_documento_complementar():
    roteiro_operador = ROTEIRO_OPERADOR.read_text(encoding="utf-8")

    assert "docs/homologacao/roundtrip-planilha-classificada.md" in roteiro_operador
