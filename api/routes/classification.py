from datetime import date
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api import schemas
from api.dependencies import DB_DEPENDENCY, verify_api_key
from core.ml_engine import ClassificadorContabil
from core.models import Empresa, Transacao

router = APIRouter()


# POST - Busca as transações pendentes de classificação
@router.post("/companies/{company_id}/classification")
def trigger_classification(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(verify_api_key),
):
    empresa = db.query(Empresa).filter(Empresa.id == company_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    """Dispara a classificação das transações pendentes"""
    engine_ml = ClassificadorContabil(db)
    # Treina o modelo com o histórico da empresa
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
    print(f"--- Classificando {len(ids_for_process)} transações...")
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
    response_model=schemas.PredictResponse,
)
def predict_transactions(
    company_id: int,
    payload: Union[schemas.PredictInput, list[schemas.PredictInput]],
    persist: bool = Query(False),
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(verify_api_key),
):
    empresa = db.query(Empresa).filter(Empresa.id == company_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not empresa.is_active:
        raise HTTPException(status_code=400, detail="Empresa está desativada")

    inputs = payload if isinstance(payload, list) else [payload]
    inputs_data = [item.model_dump() for item in inputs]

    engine_ml = ClassificadorContabil(db)
    success_train = engine_ml.train_for_company(company_id)
    if not success_train:
        raise HTTPException(
            status_code=500,
            detail="Erro ao treinar o modelo. Dados insuficientes para classificar",
        )

    predictions = engine_ml.predict_inputs(inputs_data)

    if persist:
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
