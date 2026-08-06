"""Tipos e allowlist de eventos notificáveis da esteira de agentes.

Define quais estados operacionais (`agent:*`) geram alerta em Teams/e-mail.
Fonte canônica: spec 14 §Notificações (docs/specs/14-esteira-agentes-supervisionada.md).
"""

from __future__ import annotations

from enum import Enum


class EstadoAgente(str, Enum):
    """Estados operacionais da esteira (mutuamente exclusivos)."""

    AWAITING_TASK_REVIEW = "agent:awaiting-task-review"
    AWAITING_HUMAN = "agent:awaiting-human"
    READY_TO_IMPLEMENT = "agent:ready-to-implement"
    RUNNING = "agent:running"
    AWAITING_MANUAL_TEST = "agent:awaiting-manual-test"
    VALIDATED = "agent:validated"
    BLOCKED = "agent:blocked"
    CANCELLED = "agent:cancelled"


# Estados que disparam notificação (spec 14 §Notificações).
EVENTOS_NOTIFICAVEIS: frozenset[EstadoAgente] = frozenset(
    {
        EstadoAgente.AWAITING_TASK_REVIEW,  # Task Review pronta para aprovacao
        EstadoAgente.AWAITING_HUMAN,  # decisao bloqueante
        EstadoAgente.BLOCKED,  # timeout ou falha bloqueante / reprovacao
        EstadoAgente.AWAITING_MANUAL_TEST,  # draft pronto para teste manual
        EstadoAgente.CANCELLED,  # execucao cancelada
        EstadoAgente.VALIDATED,  # validacao concluida
    }
)


class EventoNotificavel:
    """Verifica se um estado operacional deve gerar alerta."""

    @staticmethod
    def eh_notificavel(estado: str) -> bool:
        try:
            return EstadoAgente(estado) in EVENTOS_NOTIFICAVEIS
        except ValueError:
            return False
