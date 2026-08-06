"""Endpoint HTTP de notificação da esteira de agentes.

Micro-serviço interno (rede privada) que o workflow n8n consome via
``httpRequest``. Recebe o evento bruto, roteia/sanitiza e devolve o payload
mínimo allowlisted. Não dispara canais nem possui credenciais; o n8n faz o
disparo real em Teams/e-mail. Fonte canônica: spec 14 §Notificações.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from core.agent.notificacoes.roteamento import rotear_evento

router = APIRouter(prefix="/agent/notificacoes", tags=["Agente-Notificacoes"])


@router.post("/rotear", response_model=dict[str, Any] | None)
def rotear(evento: dict[str, Any]) -> dict[str, Any] | None:
    """Recebe evento bruto e devolve o payload sanitizado ou null se silencioso.

    O n8n decide o disparo com base na resposta: payload presente => alertar;
    null => evento fora da allowlist, nada a notificar.
    """
    return rotear_evento(evento)
