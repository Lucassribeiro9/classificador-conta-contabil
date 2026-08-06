"""Roteamento e disparo de notificações da esteira de agentes.

- ``rotear_evento``: decide se um evento bruto gera alerta (allowlist de
  estados) e devolve o payload sanitizado, ou ``None`` se for silencioso.
- ``notificar``: envia o payload pelos canais (Teams/e-mail) isolando falhas;
  falha de um canal nunca altera o estado oficial do GitHub (spec 14).

Os canais são callables ``(payload) -> bool`` injetados pelo chamador (o n8n,
no fluxo real). Este módulo não possui credenciais nem dispara nada sozinho.
"""

from __future__ import annotations

from typing import Any, Callable

from core.agent.notificacoes.eventos import EventoNotificavel
from core.agent.notificacoes.payload import sanitizar_evento

Canal = Callable[[dict[str, Any]], bool]


def rotear_evento(evento_bruto: dict[str, Any]) -> dict[str, Any] | None:
    """Devolve o payload sanitizado se o evento for notificável, senão None."""
    estado = evento_bruto.get("state")
    if not EventoNotificavel.eh_notificavel(estado or ""):
        return None
    return sanitizar_evento(evento_bruto)


def notificar(
    evento_bruto: dict[str, Any],
    canais: dict[str, Canal],
) -> dict[str, Any]:
    """Envia o payload pelos canais, isolando falhas.

    Retorna um dicionário com ``entregue`` (True se ao menos um canal ok) e
    ``erros`` (mapa canal -> mensagem, para registro privado). Falha de canal
    não altera e não propaga estado do GitHub.
    """
    payload = rotear_evento(evento_bruto)
    if payload is None:
        return {"entregue": False, "erros": {"roteamento": "evento silencioso"}}

    erros: dict[str, str] = {}
    entregue = False
    for nome, enviar in canais.items():
        try:
            enviar(payload)
            entregue = True
        except Exception as exc:  # falha de canal registrada privadamente
            erros[nome] = str(exc)

    return {"entregue": entregue, "erros": erros}
