import logging
from datetime import date
from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas import (
    MLClassificationInput,
    MLCriticalClassesRequest,
    MLStatusResponse,
    MLJobAccepted,
    MLJobStatus,
    PredictInput,
    PredictResponse,
)
from api.dependencies import DB_DEPENDENCY, get_current_user, require_company_access, verify_company
from core.audit import record_audit_event
from core.dataset_builder import build_dataset_treino_contrapartida
from core.ml_engine import ClassificadorContabil
from core.ml_jobs import IdempotencyConflict, enqueue_ml_job
from core.model_versions import (
    ModelLifecycleError,
    change_active_version,
)
from core.config import settings
from core.models import Empresa, MLJob, ModelVersion, Transacao, Usuario

router = APIRouter()
logger = logging.getLogger(__name__)


def _company_ml_job(db: Session, company_id: int, job_id: int) -> MLJob:
    job = db.scalar(select(MLJob).where(
        MLJob.id == job_id, MLJob.empresa_id == company_id,
    ))
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


def _ml_job_status(job: MLJob) -> MLJobStatus:
    return MLJobStatus(
        empresa_id=job.empresa_id, job_id=job.id, kind=job.kind, pool=job.pool,
        status=job.status, progress=job.progress, attempts=job.attempts,
        cancel_requested=job.cancel_requested,
        result=job.result if job.status == "completed" else None,
        error_code=job.error_code if job.status == "failed" else None,
    )


@router.get("/companies/{company_id}/ml/jobs/{job_id}", response_model=MLJobStatus)
def get_company_ml_job(
    company_id: int, job_id: int, db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("leitura")),
):
    return _ml_job_status(_company_ml_job(db, company_id, job_id))


@router.post("/companies/{company_id}/ml/jobs/{job_id}/cancel", response_model=MLJobStatus)
def cancel_company_ml_job(
    company_id: int, job_id: int, db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
):
    job = _company_ml_job(db, company_id, job_id)
    if job.status == "queued":
        job.status = "cancelled"
    elif job.status == "running":
        job.cancel_requested = True
    elif job.status != "cancelled":
        raise HTTPException(status_code=409, detail="Job não pode ser cancelado")
    record_audit_event(db, event_type="ml.job.cancel_requested", empresa_id=company_id,
                       resource_id=str(job.id), metadata={"status": job.status})
    db.commit()
    return _ml_job_status(job)


@router.post("/companies/{company_id}/ml/jobs/{job_id}/retry", response_model=MLJobStatus)
def retry_company_ml_job(
    company_id: int, job_id: int, db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
):
    job = _company_ml_job(db, company_id, job_id)
    if job.status != "failed":
        raise HTTPException(status_code=409, detail="Somente job falho pode ser reenfileirado")
    job.status = "queued"
    job.attempts = 0
    job.progress = 0
    job.error_code = None
    job.cancel_requested = False
    record_audit_event(db, event_type="ml.job.manual_retry", empresa_id=company_id,
                       resource_id=str(job.id), metadata={})
    db.commit()
    return _ml_job_status(job)


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
    response_model=MLJobAccepted,
    status_code=202,
)
def classify_lancamentos_with_saved_model(
    company_id: int,
    payload: Union[MLClassificationInput, list[MLClassificationInput]],
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
    current_user: Usuario = Depends(get_current_user),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    """Enfileira classificacao canonica sem executar inferencia no HTTP."""
    inputs = payload if isinstance(payload, list) else [payload]
    if len(inputs) > 100:
        raise HTTPException(status_code=422, detail="Limite de 100 lançamentos por requisição")
    try:
        job = enqueue_ml_job(
            db, company_id=company_id, kind="classify",
            idempotency_key=idempotency_key,
            requested_by=current_user.id,
            payload={"inputs": [item.model_dump(mode="json") for item in inputs]},
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job_id, status = job.id, job.status
    db.commit()
    return {
        "empresa_id": company_id, "job_id": job_id, "status": status,
        "status_url": f"/api/v1/companies/{company_id}/ml/jobs/{job_id}",
    }


@router.post(
    "/companies/{company_id}/ml/train",
    response_model=MLJobAccepted,
    status_code=202,
)
def train_company_ml_model_from_canonical_razao(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    _empresa: Empresa = Depends(require_company_access("operacao")),
    current_user: Usuario = Depends(get_current_user),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    """Enfileira treino canonico sem executar ML na requisicao HTTP."""
    try:
        job = enqueue_ml_job(
            db, company_id=company_id, kind="train",
            idempotency_key=idempotency_key, payload={},
            requested_by=current_user.id,
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job_id, status = job.id, job.status
    db.commit()
    return {
        "empresa_id": company_id,
        "job_id": job_id,
        "status": status,
        "status_url": f"/api/v1/companies/{company_id}/ml/jobs/{job_id}",
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
