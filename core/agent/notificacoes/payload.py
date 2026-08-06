"""Sanitização de payload de notificação (função pura, allowlist estrita).

Garante que nenhum campo proibido (segredo, URL privada, prompt, diff, log,
dado contábil, comando) chegue ao payload nem ao log. Fonte canônica: spec 14
§Notificações e §Telemetria Privada.
"""

from __future__ import annotations

from typing import Any

# Campos permitidos no payload de notificação (spec 14 §Notificações).
_CAMPOS_ALLOWLIST: frozenset[str] = frozenset(
    {
        "repository",
        "issue_number",
        "title",
        "state",
        "resumo_sanitizado",
        "acao_esperada",
        "link",
    }
)

# Chaves que nunca devem aparecer no payload (mesmo que presentes no evento bruto).
_CAMPOS_PROIBIDOS: frozenset[str] = frozenset(
    {
        "secret",
        "token",
        "url_privada",
        "prompt",
        "diff",
        "log",
        "dado_contabil",
        "comando",
        "credential",
        "signature",
        "private_url",
        "consumo",
    }
)


def sanitizar_evento(evento_bruto: dict[str, Any]) -> dict[str, Any]:
    """Recebe o evento bruto e devolve o payload mínimo allowlisted.

    Campos proibidos são descartados silenciosamente. O resumo bruto é
    renomeado para ``resumo_sanitizado`` e só o permitido é preservado.
    """
    resumo = evento_bruto.get("resumo")
    payload: dict[str, Any] = {
        "repository": evento_bruto.get("repository"),
        "issue_number": evento_bruto.get("issue_number"),
        "title": evento_bruto.get("title"),
        "state": evento_bruto.get("state"),
        "resumo_sanitizado": resumo,
        "acao_esperada": evento_bruto.get("acao_esperada"),
        "link": evento_bruto.get("link"),
    }
    # Seguranca defensiva: remove qualquer chave proibida que por engano
    # tenha sido injetada no dicionario resultante.
    for campo in _CAMPOS_PROIBIDOS:
        payload.pop(campo, None)
    return payload
