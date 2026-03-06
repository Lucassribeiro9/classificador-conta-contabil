import logging
from datetime import date
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas import PredictInput, PredictResponse
from api.dependencies import DB_DEPENDENCY, verify_company
from core.ml_engine import ClassificadorContabil
from core.models import Empresa, Transacao

router = APIRouter()
logger = logging.getLogger(__name__)


# Decisão de domínio:
# - /classification: processa pendências já persistidas no banco (conta_contabil nula).
# - /predict: inferência sob demanda para payload externo, com persistência opcional.
# - /feedback continua sendo o fluxo de correção humana de uma classificação já atribuída.
@router.post("/companies/{company_id}/classification")
def trigger_classification(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Classifica transações pendentes da empresa já salvas no banco."""

    engine_ml = ClassificadorContabil(db)
    # Nota: hoje o modelo é treinado por requisição.
    # Manter assim por enquanto, com otimização futura via cache/reuso por empresa.
    success_train = engine_ml.train_for_company(company_id)
    if not success_train:
        raise HTTPException(
            status_code=500,
            detail="Erro ao treinar o modelo. Dados insuficientes para classificar",
        )

    # Busca ID das transações sem conta
    pendentes = (
        db.query(Transacao)
        .filter(
            Transacao.empresa_id == company_id,
            Transacao.conta_contabil == None,
        )
        .all()
    )
    if not pendentes:
        return {"message": "Nenhuma transação pendente encontrada"}
    ids_for_process = [t.id for t in pendentes]
    logger.info(
        "Classificando transacoes pendentes",
        extra={"company_id": company_id, "total_transacoes": len(ids_for_process)},
    )
    # Executa o classificador
    try:
        resultados = engine_ml.classify_transactions(company_id, ids_for_process)
        return {
            "status": "sucesso",
            "empresa_id": company_id,
            "quantidade_processada": len(resultados),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao classificar transações: {e}"
        )


@router.post(
    "/companies/{company_id}/predict",
    response_model=PredictResponse,
)
def predict_transactions(
    company_id: int,
    payload: Union[PredictInput, list[PredictInput]],
    persist: bool = Query(False),
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(verify_company),
):
    """Prediz conta contábil para entradas externas; persiste somente se persist=true."""

    if not empresa.is_active:
        raise HTTPException(status_code=400, detail="Empresa está desativada")

    inputs = payload if isinstance(payload, list) else [payload]
    inputs_data = [item.model_dump() for item in inputs]

    engine_ml = ClassificadorContabil(db)
    # Mesma observação de performance: treino é feito por request no estado atual.
    success_train = engine_ml.train_for_company(company_id)
    if not success_train:
        raise HTTPException(
            status_code=500,
            detail="Erro ao treinar o modelo. Dados insuficientes para classificar",
        )

    predictions = engine_ml.predict_inputs(inputs_data)

    if persist:
        # Persistência opcional de predições para transformar inferência em registro transacional.
        persist_rows = []
        for item, prediction in zip(inputs_data, predictions):
            persist_rows.append(
                Transacao(
                    empresa_id=company_id,
                    data=date.today(),
                    cod_banco=item.get("cod_banco"),
                    historico=item["historico"],
                    valor=0,
                    conta_contabil=prediction["conta_contabil_predita"],
                    confidence=prediction["confidence"],
                    needs_review=prediction["needs_review"],
                    is_classified=True,
                )
            )
        db.add_all(persist_rows)
        db.commit()

    return {
        "empresa_id": company_id,
        "quantidade_processada": len(predictions),
        "persisted": persist,
        "results": predictions,
    }
