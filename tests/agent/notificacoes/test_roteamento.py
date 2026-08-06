import json
from pathlib import Path

from core.agent.notificacoes.eventos import EventoNotificavel
from core.agent.notificacoes.payload import sanitizar_evento
from core.agent.notificacoes.roteamento import rotear_evento, notificar

FIXTURES = Path(__file__).parent / "fixtures"


def _carregar(nome):
    return json.loads((FIXTURES / nome).read_text(encoding="utf-8"))


def test_eventos_notificaveis_geram_payload_allowlisted():
    dados = _carregar("eventos_notificaveis.json")
    for caso in dados["eventos"]:
        payload = rotear_evento(caso["raw"])
        assert payload is not None, f"evento {caso['id']} deveria gerar alerta"
        esperado = caso["esperado"]
        assert payload["repository"] == esperado["repository"]
        assert payload["issue_number"] == esperado["issue_number"]
        assert payload["title"] == esperado["title"]
        assert payload["state"] == esperado["state"]
        assert payload["resumo_sanitizado"] == esperado["resumo_sanitizado"]
        assert payload["acao_esperada"] == esperado["acao_esperada"]
        assert payload["link"] == esperado["link"]


def test_eventos_silenciosos_nao_geram_alerta():
    dados = _carregar("eventos_silenciosos.json")
    for caso in dados["eventos"]:
        payload = rotear_evento(caso["raw"])
        assert payload is None, f"evento {caso['id']} nao deveria gerar alerta"


def test_sanitizacao_remove_campos_proibidos():
    bruto = {
        "repository": "Lucassribeiro9/classificador-conta-contabil",
        "issue_number": 379,
        "title": "titulo",
        "state": "agent:awaiting-task-review",
        "resumo": "resumo normal",
        "acao_esperada": "acao",
        "link": "https://github.com/x/issues/379",
        "secret": "ghp_XXXX",
        "url_privada": "https://10.0.0.1/internal",
        "prompt": "system: faca X",
        "diff": "--- a/file.py",
        "log": "ERROR traceback",
        "dado_contabil": "R$ 1.000,00",
        "comando": "rm -rf /",
    }
    payload = sanitizar_evento(bruto)
    proibidos = {"secret", "url_privada", "prompt", "diff", "log", "dado_contabil", "comando"}
    for campo in proibidos:
        assert campo not in payload, f"campo proibido {campo} vazou no payload"


def test_sanitizacao_preserva_campos_allowlisted():
    bruto = {
        "repository": "Lucassribeiro9/classificador-conta-contabil",
        "issue_number": 379,
        "title": "titulo",
        "state": "agent:awaiting-task-review",
        "resumo": "resumo",
        "acao_esperada": "acao",
        "link": "https://github.com/x/issues/379",
    }
    payload = sanitizar_evento(bruto)
    assert set(payload.keys()) == {
        "repository",
        "issue_number",
        "title",
        "state",
        "resumo_sanitizado",
        "acao_esperada",
        "link",
    }


def test_falha_de_canal_nao_altera_estado_github():
    dados = _carregar("falha_canais.json")
    for caso in dados["canais"]:
        github_state = caso["github_state_esperado"]
        falhas = caso["canais_que_falham"]

        def _canal_falho(nome):
            def _enviar(payload):
                if nome in falhas:
                    raise RuntimeError(f"canal {nome} indisponivel")
                return True

            return _enviar

        canais = {
            "teams": _canal_falho("teams"),
            "email": _canal_falho("email"),
        }
        # notificar nao deve lancar e nao deve alterar github_state
        resultado = notificar(caso["evento"], canais)
        assert github_state == caso["github_state_esperado"]
        assert resultado["entregue"] in (True, False)
        # se algum canal falhou, deve estar registrado (privado), nao propagado
        assert "erros" in resultado


def test_falha_dupla_registra_sem_corromper():
    dados = _carregar("falha_canais.json")
    caso = next(c for c in dados["canais"] if c["id"] == "falha_dupla")

    def _falha(nome):
        def _enviar(payload):
            raise RuntimeError(f"canal {nome} indisponivel")

        return _enviar

    canais = {"teams": _falha("teams"), "email": _falha("email")}
    resultado = notificar(caso["evento"], canais)
    assert resultado["entregue"] is False
    assert len(resultado["erros"]) == 2
    assert caso["github_state_esperado"] == "agent:awaiting-task-review"
