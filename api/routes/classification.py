import logging
from datetime import date
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas import (
    MLClassificationInput,
    MLClassificationResponse,
    MLTrainResponse,
    PredictInput,
    PredictResponse,
)
from api.dependencies import DB_DEPENDENCY, require_company_access, verify_company
from core.audit import record_audit_event
from core.dataset_builder import build_dataset_treino_contrapartida
from core.ml_engine import ClassificadorContabil
from core.models import ContaContabil, Empresa, Transacao

router = APIRouter()
logger = logging.getLogger(__name__)


# Decisão de domínio:
# - /classification: processa pendências já persistidas no banco (conta_contabil nula).
# - /predict: inferência sob demanda para payload externo, com persistência opcional.
# - /feedback continua sendo o fluxo de correção humana de uma classificação já atribuída.

# Helper - Tratamento para dados insuficientes:
INSUFFICIENT_TRAINING_DATA = "Dados insuficientes para classificação. São necessárias ao menos 10 transações com conta contábil preenchida"

def _train_or_raise(engine_ml: ClassificadorContabil, company_id: int):
    """
    Tenta treinar o modelo de classificação para uma empresa.
    Se a empresa não tiver ao menos 10 transações com conta contábil preenchida,
    lança uma exceção HTTP 422 com detalhes "Dados insuficientes para classificação".
    """
    try:
        success_train = engine_ml.train_for_company(company_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=INSUFFICIENT_TRAINING_DATA)
    if not success_train:
        raise HTTPException(status_code=422, detail=INSUFFICIENT_TRAINING_DATA)


@router.post(
    "/companies/{company_id}/ml/classification",
    response_model=MLClassificationResponse,
)
def classify_lancamentos_with_saved_model(
    company_id: int,
    payload: Union[MLClassificationInput, list[MLClassificationInput]],
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
):
    inputs = payload if isinstance(payload, list) else [payload]
    if len(inputs) > 100:
        raise HTTPException(
            status_code=422,
            detail="Limite de 100 lançamentos por requisição",
        )

    engine_ml = ClassificadorContabil(db)
    record_audit_event(
        db,
        event_type="classification.started",
        empresa_id=company_id,
        resource_id="ml_classification",
        metadata={"total_solicitado": len(inputs)},
    )
    if not engine_ml.model_exists_for_company(company_id):
        record_audit_event(
            db,
            event_type="classification.failed",
            empresa_id=company_id,
            resource_id="ml_classification",
            metadata={
                "total_solicitado": len(inputs),
                "error_type": "ModelNotFound",
                "reason": "model_not_found",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="Modelo treinado não encontrado para a empresa",
        )

    try:
        predictions = engine_ml.classify_lancamentos_from_saved_model(
            empresa_id=company_id,
            lancamentos=[item.model_dump() for item in inputs],
        )
    except Exception as exc:
        record_audit_event(
            db,
            event_type="classification.failed",
            empresa_id=company_id,
            resource_id="ml_classification",
            metadata={
                "total_solicitado": len(inputs),
                "error_type": type(exc).__name__,
                "reason": "classification_error",
            },
        )
        db.commit()
        raise

    predicted_accounts = {
        prediction["conta_contrapartida"] for prediction in predictions
    }
    valid_accounts = {
        conta.codigo
        for conta in db.query(ContaContabil)
        .filter(ContaContabil.codigo.in_(predicted_accounts))
        .filter(ContaContabil.tipo == "A")
        .filter(ContaContabil.is_active.is_(True))
        .all()
    }
    invalid_accounts = predicted_accounts - valid_accounts
    if invalid_accounts:
        record_audit_event(
            db,
            event_type="classification.failed",
            empresa_id=company_id,
            resource_id="ml_classification",
            metadata={
                "total_solicitado": len(inputs),
                "total_processado": len(predictions),
                "error_type": "InvalidPredictedAccount",
                "reason": "invalid_predicted_account",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=422,
            detail="Modelo retornou conta de contrapartida inválida",
        )

    record_audit_event(
        db,
        event_type="classification.completed",
        empresa_id=company_id,
        resource_id="ml_classification",
        metadata={
            "total_processado": len(predictions),
            "total_revisao": sum(
                1 for prediction in predictions if prediction["needs_review"]
            ),
        },
    )
    db.commit()

    return {
        "empresa_id": company_id,
        "quantidade_processada": len(predictions),
        "results": predictions,
    }


@router.post(
    "/companies/{company_id}/ml/train",
    response_model=MLTrainResponse,
)
def train_company_ml_model_from_canonical_razao(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
):
    """Treina o modelo canonico de contrapartida a partir do Razao da empresa."""
    dataset = build_dataset_treino_contrapartida(db, empresa_id=company_id)
    engine_ml = ClassificadorContabil(db)
    trained = engine_ml.train_from_dataset(dataset)
    if not trained:
        db.commit()
        raise HTTPException(
            status_code=422,
            detail="Dataset insuficiente para treino do modelo",
        )

    db.commit()
    metadata = dataset.metadata
    return {
        "empresa_id": company_id,
        "total_linhas": metadata["total_linhas"],
        "total_descartes": metadata["total_descartes"],
        "contagem_por_target": metadata["contagem_por_target"],
        "treinavel": metadata["treinavel"],
        "status": "trained",
    }


@router.post("/companies/{company_id}/classification")
def trigger_classification(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(verify_company),
):
    """Classifica transações pendentes da empresa já salvas no banco."""

    engine_ml = ClassificadorContabil(db)
    _train_or_raise(engine_ml, company_id)
    # Nota: hoje o modelo é treinado por requisição.
    # Manter assim por enquanto, com otimização futura via cache/reuso por empresa.
    
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
    _train_or_raise(engine_ml, company_id)
    # Mesma observação de performance: treino é feito por request no estado atual.
    
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
