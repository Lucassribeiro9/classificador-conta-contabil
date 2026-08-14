from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROTEIRO = ROOT / "docs/homologacao/roteiro-ciclo-0.md"


def read_roteiro() -> str:
    return ROTEIRO.read_text(encoding="utf-8")


def test_roteiro_ciclo0_existe_e_referencia_contexto_canonico():
    roteiro = read_roteiro()

    assert "# Roteiro de Homologacao Formal do Ciclo 0" in roteiro
    assert "Fase 3 / Release 1 / Ciclo 0" in roteiro
    assert "docs/specs/15-harness-qualidade-documentacao.md" in roteiro
    assert "docs/homologacao-checklist-tecnico.md" in roteiro
    assert "docs/homologacao-roteiro-operador-contador.md" in roteiro
    assert "docs/frontend-homologacao-mvp-ux.md" in roteiro
    assert "docs/homologacao-smoke-aplicacao.md" in roteiro


def test_roteiro_ciclo0_contem_campos_obrigatorios_da_spec15():
    roteiro = read_roteiro()

    for campo in [
        "Ambiente",
        "Commit testado",
        "Responsavel pela execucao",
        "Perfil utilizado",
        "Servicos necessarios",
        "Roteiro executado",
        "Evidencias tratadas",
        "Divergencias",
        "Decisao final",
    ]:
        assert campo in roteiro


def test_roteiro_ciclo0_define_resultados_e_decisoes_permitidas():
    roteiro = read_roteiro()

    for resultado in ["APROVADO", "REPROVADO", "BLOQUEADO", "NAO APLICAVEL"]:
        assert resultado in roteiro
    assert "APROVADO COM RESSALVAS" in roteiro


def test_roteiro_ciclo0_exige_evidencias_sanitizadas_e_divergencias_rastreaveis():
    roteiro = read_roteiro()

    for coluna in [
        "| Tipo | Referencia | Conteudo resumido | Sanitizacao aplicada | Responsavel |",
        "| ID | Cenario | Severidade | Responsavel | Encaminhamento | Link ou issue |",
    ]:
        assert coluna in roteiro

    for proibicao in [
        "Nao versione evidencias reais",
        "Nao registre senhas, tokens, segredos",
        "dados contabeis reais",
    ]:
        assert proibicao in roteiro


def test_roteiro_ciclo0_inclui_exemplo_sanitizado():
    roteiro = read_roteiro()

    assert "## Exemplo de preenchimento sanitizado" in roteiro
    assert "EMPRESA MODELO HOMOLOGACAO LTDA" in roteiro
    assert "usuario.operador.hml" in roteiro
    assert "APROVADO COM RESSALVAS" in roteiro
