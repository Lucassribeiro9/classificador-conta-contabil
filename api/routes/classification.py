import logging
from datetime import date
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas import (
    MLClassificationInput,
    MLClassificationResponse,
    MLCriticalClassesRequest,
    MLStatusResponse,
    MLTrainResponse,
    PredictInput,
    PredictResponse,
)
from api.dependencies import DB_DEPENDENCY, require_company_access, verify_company
from core.audit import record_audit_event
from core.conta_contabil_empresa import garantir_identidade_contabil
from core.dataset_builder import build_dataset_treino_contrapartida
from core.ml_engine import ClassificadorContabil
from core.model_versions import (
    ModelLifecycleError,
    change_active_version,
    create_candidate,
)
from core.config import settings
from core.models import Empresa, ModelVersion, Transacao

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
    response_model_exclude_none=True,
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
    contas_contextuais = [
        garantir_identidade_contabil(
            db, empresa_id=company_id, codigo=codigo
        )
        for codigo in predicted_accounts
    ]
    valid_accounts = {
        conta.codigo
        for conta in contas_contextuais
        if conta is not None and conta.is_classificavel
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

    active_version_id = engine_ml.active_model_version_id_for_company(company_id)
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
            **({"model_version_id": active_version_id} if active_version_id else {}),
        },
    )
    db.commit()

    return {
        "empresa_id": company_id,
        "quantidade_processada": len(predictions),
        "results": predictions,
        "model_version_id": active_version_id,
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
    if not dataset.metadata.get("treinavel", False):
        record_audit_event(
            db,
            event_type="model.train_failed",
            empresa_id=company_id,
            metadata={"reason": "insufficient_dataset", "dataset_examples": dataset.metadata["total_linhas"]},
        )
        db.commit()
        raise HTTPException(
            status_code=422,
            detail="Dataset insuficiente para treino do modelo",
        )

    version = create_candidate(
        db, dataset, model_dir=settings.MODEL_DIR,
        critical_classes=_empresa.ml_critical_classes,
    )
    db.commit()
    metadata = dataset.metadata
    return {
        "empresa_id": company_id,
        "version_id": version.id,
        "total_linhas": metadata["total_linhas"],
        "total_descartes": metadata["total_descartes"],
        "contagem_por_target": metadata["contagem_por_target"],
        "treinavel": metadata["treinavel"],
        "status": "candidate",
    }


@router.put("/companies/{company_id}/ml/critical-classes")
def set_company_ml_critical_classes(
    company_id: int,
    payload: MLCriticalClassesRequest,
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(require_company_access("admin_empresa")),
):
    if len(payload.classes) > 100 or any(value <= 0 for value in payload.classes):
        raise HTTPException(status_code=422, detail="Lista de classes criticas invalida")
    empresa.ml_critical_classes = sorted(set(payload.classes))
    record_audit_event(
        db, event_type="model.critical_classes_updated", empresa_id=company_id,
        metadata={"total_classes": len(empresa.ml_critical_classes)},
    )
    db.commit()
    return {"empresa_id": company_id, "classes": empresa.ml_critical_classes}


@router.get("/companies/{company_id}/ml/models")
def list_company_ml_models(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("admin_empresa")),
):
    versions = db.scalars(
        select(ModelVersion).where(ModelVersion.empresa_id == company_id)
        .order_by(ModelVersion.id.desc())
    ).all()
    return {
        "empresa_id": company_id,
        "models": [
            {
                "id": version.id,
                "status": version.status,
                "manifest_id": version.manifest_id,
                "threshold": version.threshold,
                "metrics": version.metrics,
                "evaluation": version.evaluation,
                "critical_classes": version.critical_classes,
                "created_at": version.created_at.isoformat(),
            }
            for version in versions
        ],
    }


@router.post("/companies/{company_id}/ml/models/{version_id}/promote")
def promote_company_model(
    company_id: int,
    version_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("admin_empresa")),
):
    try:
        version = change_active_version(
            db, company_id=company_id, version_id=version_id,
            model_dir=settings.MODEL_DIR,
        )
    except ModelLifecycleError as exc:
        db.rollback()
        record_audit_event(
            db, event_type="model.promotion_denied", empresa_id=company_id,
            resource_id=str(version_id), metadata={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"empresa_id": company_id, "version_id": version.id, "status": version.status}


@router.post("/companies/{company_id}/ml/models/{version_id}/rollback")
def rollback_company_model(
    company_id: int,
    version_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("admin_empresa")),
):
    try:
        version = change_active_version(
            db, company_id=company_id, version_id=version_id,
            model_dir=settings.MODEL_DIR, rollback=True,
        )
    except ModelLifecycleError as exc:
        db.rollback()
        record_audit_event(
            db, event_type="model.rollback_denied", empresa_id=company_id,
            resource_id=str(version_id), metadata={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"empresa_id": company_id, "version_id": version.id, "status": version.status}


@router.get(
    "/companies/{company_id}/ml/status",
    response_model=MLStatusResponse,
)
def get_company_ml_status(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("leitura")),
):
    """Consulta se a empresa tem dataset treinavel e modelo canonico salvo."""
    dataset = build_dataset_treino_contrapartida(db, empresa_id=company_id)
    db.commit()
    metadata = dataset.metadata
    engine_ml = ClassificadorContabil(db)
    modelo_existente = engine_ml.model_exists_for_company(company_id)
    treinavel = metadata["treinavel"]
    dataset_total_linhas = metadata["total_linhas"]
    if dataset_total_linhas == 0 and metadata["total_descartes"] == 0:
        status = "sem_razao"
    elif not treinavel:
        status = "dataset_insuficiente"
    elif not modelo_existente:
        status = "treinavel_sem_modelo"
    else:
        status = "modelo_pronto"

    return {
        "empresa_id": company_id,
        "dataset_total_linhas": dataset_total_linhas,
        "dataset_total_descartes": metadata["total_descartes"],
        "contagem_por_target": metadata["contagem_por_target"],
        "treinavel": treinavel,
        "modelo_existente": modelo_existente,
        "modelo_path": engine_ml.model_relative_path_for_company(company_id)
        if modelo_existente else None,
        "pode_classificar_movimentos": treinavel and modelo_existente,
        "status": status,
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
            Transacao.conta_contabil.is_(None),
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
