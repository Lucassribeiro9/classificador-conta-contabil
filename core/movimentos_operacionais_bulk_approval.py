from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import EmpresaContaContabil, MovimentoOperacionalImportado


def aprovar_movimentos_operacionais_em_lote(
    session: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    movimento_ids: list[int],
) -> dict[str, list[dict[str, Any]]]:
    """Aprova em lote apenas movimentos operacionais elegiveis."""

    result: dict[str, list[dict[str, Any]]] = {
        "aprovados": [],
        "ignorados": [],
        "erros": [],
    }
    contas_vinculadas = _load_contas_vinculadas(session, empresa_id)

    for movimento_id in movimento_ids:
        movimento = session.get(MovimentoOperacionalImportado, movimento_id)
        if movimento is None or movimento.empresa_id != empresa_id:
            result["erros"].append(
                {"id": movimento_id, "erro": "movimento_nao_encontrado"}
            )
            continue

        eligibility = _bulk_approval_eligibility(movimento, contas_vinculadas)
        if eligibility["eligible"] is not True:
            result["ignorados"].append(
                {"id": movimento.id, "motivo": str(eligibility["motivo"])}
            )
            continue

        conta_final = int(eligibility["conta_final"])
        _approve_movimento(movimento, conta_final)
        result["aprovados"].append({"id": movimento.id, "conta_final": conta_final})

    _audit_bulk_approval(
        session,
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        movimento_ids=movimento_ids,
        result=result,
    )
    session.flush()
    return result


def _bulk_approval_eligibility(
    movimento: MovimentoOperacionalImportado,
    contas_vinculadas: set[int],
) -> dict[str, Any]:
    """Avalia se o movimento pode ser aprovado sem acao individual."""

    if movimento.status == "pre_classificado":
        conta_final = movimento.contrapartida_informada
    elif movimento.status == "sugerido":
        if movimento.confidence_sugerida is None or movimento.confidence_sugerida < 0.70:
            return {"eligible": False, "motivo": "baixa_confianca"}
        conta_final = movimento.contrapartida_sugerida
    else:
        return {"eligible": False, "motivo": "movimento_nao_elegivel"}

    if movimento.mensagens_validacao:
        return {"eligible": False, "motivo": "movimento_nao_elegivel"}
    if conta_final is None:
        return {"eligible": False, "motivo": "contrapartida_ausente"}
    if movimento.conta_financeira not in contas_vinculadas:
        return {"eligible": False, "motivo": "conta_financeira_nao_vinculada"}
    if int(conta_final) not in contas_vinculadas:
        return {"eligible": False, "motivo": "contrapartida_nao_vinculada"}

    return {"eligible": True, "conta_final": int(conta_final)}


def _approve_movimento(
    movimento: MovimentoOperacionalImportado,
    conta_final: int,
) -> None:
    """Marca movimento como aprovado e persiste par debito/credito final."""

    movimento.contrapartida_final = conta_final
    movimento.status = "aprovado"
    movimento.elegivel_treino = True
    if movimento.direcao == "debito":
        movimento.conta_debito = movimento.conta_financeira
        movimento.conta_credito = conta_final
    else:
        movimento.conta_debito = conta_final
        movimento.conta_credito = movimento.conta_financeira


def _load_contas_vinculadas(session: Session, empresa_id: int) -> set[int]:
    """Carrega contas ja vinculadas a empresa sem criar novas relacoes."""

    rows = session.execute(
        select(EmpresaContaContabil.conta_codigo).where(
            EmpresaContaContabil.empresa_id == empresa_id
        )
    ).all()
    return {row[0] for row in rows}


def _audit_bulk_approval(
    session: Session,
    *,
    empresa_id: int,
    usuario_id: int,
    movimento_ids: list[int],
    result: dict[str, list[dict[str, Any]]],
) -> None:
    """Registra auditoria da aprovacao em lote sem dados sensiveis."""

    aprovados = [item["id"] for item in result["aprovados"]]
    ignorados = [item["id"] for item in result["ignorados"]]
    erros = [item["id"] for item in result["erros"]]
    record_audit_event(
        session,
        event_type="operational_movements.bulk_approved",
        user_id=usuario_id,
        empresa_id=empresa_id,
        metadata={
            "movimento_ids": movimento_ids,
            "aprovados": aprovados,
            "ignorados": ignorados,
            "erros": erros,
            "total_aprovados": len(aprovados),
            "total_ignorados": len(ignorados),
            "total_erros": len(erros),
        },
    )
