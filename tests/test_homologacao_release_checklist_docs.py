from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/homologacao-checklist-tecnico.md"


def read_checklist() -> str:
    return " ".join(CHECKLIST.read_text(encoding="utf-8").lower().split())


def test_checklist_requires_all_technical_release_gates():
    checklist = read_checklist()

    required_gates = (
        "backend tests relevantes",
        "frontend lint",
        "frontend typecheck",
        "frontend build",
        "docker compose de homologacao",
        "banco de homologacao separado de producao",
        "api `/health`",
        "tela de login",
        "usuario operador/contador de teste",
        "empresas e permissoes de teste",
        "massa sanitizada",
    )

    for gate in required_gates:
        assert gate in checklist


def test_checklist_defines_blockers_evidence_and_ownership():
    checklist = read_checklist()

    required_content = (
        "## criterios de bloqueio",
        "uso de dados reais ou sensiveis",
        "ambiente ou banco compartilhado com producao",
        "falha de autenticacao ou permissao por empresa",
        "melhoria cosmetica nao bloqueia",
        "## evidencias minimas",
        "comando executado e resultado",
        "identificador sanitizado",
        "nao registre senhas, tokens, segredos",
        "responsavel tecnico",
        "responsavel pela homologacao",
        "justificativa obrigatoria",
    )

    for content in required_content:
        assert content in checklist
