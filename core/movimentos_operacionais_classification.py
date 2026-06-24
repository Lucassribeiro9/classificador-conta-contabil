from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.ml_engine import ClassificadorContabil
from core.models import MovimentoOperacionalImportado


def classificar_movimentos_operacionais_pendentes(
    session: Session,
    *,
    empresa_id: int,
    model_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Classifica movimentos operacionais pendentes de uma empresa.

    A classificacao usa o modelo treinado a partir do dataset canonico do Razao
    e persiste apenas sugestao, confianca e status. A decisao final continua
    dependendo de revisao humana.
    """
    movimentos = (
        session.query(MovimentoOperacionalImportado)
        .filter(MovimentoOperacionalImportado.empresa_id == empresa_id)
        .filter(MovimentoOperacionalImportado.status == "pendente")
        .order_by(MovimentoOperacionalImportado.id.asc())
        .all()
    )
    if not movimentos:
        result = _result(empresa_id=empresa_id, total_sugerido=0, total_revisao=0)
        _audit_classification(session, result)
        session.flush()
        return result

    engine = ClassificadorContabil(session, model_dir=model_dir)
    predictions = engine.classify_operational_movements_from_saved_model(
        empresa_id=empresa_id,
        movimentos=[
            {
                "historico_normalizado": movimento.historico_normalizado,
                "conta_financeira": movimento.conta_financeira,
                "direcao": movimento.direcao,
                "tipo_movimento": movimento.tipo_movimento,
            }
            for movimento in movimentos
        ],
    )

    total_sugerido = 0
    total_revisao = 0
    for movimento, prediction in zip(movimentos, predictions):
        movimento.contrapartida_sugerida = prediction["contrapartida_sugerida"]
        movimento.confidence_sugerida = prediction["confidence_sugerida"]
        movimento.status = prediction["status"]
        if movimento.status == "sugerido":
            total_sugerido += 1
        else:
            total_revisao += 1

    result = _result(
        empresa_id=empresa_id,
        total_sugerido=total_sugerido,
        total_revisao=total_revisao,
    )
    _audit_classification(session, result)
    session.flush()
    return result


def _result(
    *,
    empresa_id: int,
    total_sugerido: int,
    total_revisao: int,
) -> dict[str, Any]:
    """Monta o resumo estavel da classificacao operacional."""
    quantidade_processada = total_sugerido + total_revisao
    return {
        "empresa_id": empresa_id,
        "quantidade_processada": quantidade_processada,
        "total_sugerido": total_sugerido,
        "total_revisao": total_revisao,
    }


def _audit_classification(session: Session, result: dict[str, Any]) -> None:
    """Registra auditoria sem historicos, documentos ou observacoes."""
    record_audit_event(
        session,
        event_type="operational_movements.classified",
        empresa_id=result["empresa_id"],
        resource_id="operational_movements_classification",
        metadata={
            "total_processado": result["quantidade_processada"],
            "total_sugerido": result["total_sugerido"],
            "total_revisao": result["total_revisao"],
        },
    )
