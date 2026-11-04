"""Versioned training and evaluation for company-scoped ML models."""

from hashlib import sha256
from pathlib import Path

import joblib
from sklearn.base import clone
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.dataset_builder import DatasetTreinoContrapartida
from core.ml_engine import ClassificadorContabil
from core.models import Empresa, ModelVersion


class ModelLifecycleError(ValueError):
    """A version cannot enter the requested state."""


def _scores(y_true, y_pred) -> dict:
    classes = sorted({int(value) for value in y_true})
    class_scores = f1_score(y_true, y_pred, labels=classes, average=None, zero_division=0)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0)),
        "per_class_f1": {
            str(label): float(score) for label, score in zip(classes, class_scores)
        },
        "support": {str(label): list(y_true).count(label) for label in classes},
    }


def _evaluate(pipeline, rows: list[dict]) -> tuple[dict, dict, list, list]:
    features = [row["features"] for row in rows]
    targets = [int(row["target_conta_contrapartida"]) for row in rows]
    counts = {label: targets.count(label) for label in set(targets)}
    if len(counts) < 2 or min(counts.values()) < 2:
        return {"method": "insufficient_support", "valid": False, "reason": "class_support_below_two"}, {}, [], []
    if min(counts.values()) >= 5:
        train_x, test_x, train_y, test_y = train_test_split(
            features, targets, test_size=0.2, stratify=targets, random_state=505
        )
        evaluator = clone(pipeline).fit(train_x, train_y)
        metrics = _scores(test_y, evaluator.predict(test_x))
        return {"method": "holdout", "valid": True, "seed": 505, "test_size": len(test_y)}, metrics, test_x, test_y
    folds = min(5, min(counts.values()))
    predictions = cross_val_predict(
        clone(pipeline), features, targets,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=505),
    )
    return {"method": "stratified_kfold", "valid": True, "seed": 505, "folds": folds}, _scores(targets, predictions), features, targets


def create_candidate(
    session: Session,
    dataset: DatasetTreinoContrapartida,
    *,
    model_dir: Path | str,
    critical_classes: list[int] | None = None,
) -> ModelVersion:
    """Train a candidate without touching the active model or legacy artifact."""
    if not dataset.metadata.get("treinavel", False):
        raise ValueError("Dataset insuficiente para treino do modelo")
    if dataset.manifesto is None or not dataset.manifesto.get("id"):
        raise ValueError("Manifesto do dataset obrigatorio")
    company_id = int(dataset.metadata["empresa_id"])
    if int(dataset.manifesto["empresa_id"]) != company_id:
        raise ValueError("Manifesto de outra empresa")
    model_dir = Path(model_dir)
    engine = ClassificadorContabil(session, model_dir=model_dir)
    evaluation, metrics, reference_features, reference_targets = _evaluate(
        engine.pipeline, dataset.linhas
    )
    current = active_version(session, company_id)
    baseline_metrics = None
    if current is not None and evaluation["valid"]:
        _verify_artifact(current, model_dir)
        baseline_model = joblib.load(model_dir / current.artifact_path)
        baseline_metrics = _scores(
            reference_targets, baseline_model.predict(reference_features)
        )
    model = ModelVersion(
        empresa_id=company_id,
        manifest_id=dataset.manifesto["id"],
        status="candidate",
        threshold=0.70,
        metrics=metrics,
        evaluation={
            **evaluation,
            "evaluation_version": "ml-eval-v1",
            "manifest_hash": dataset.manifesto["hash"],
            "comparison_version_id": current.id if current is not None else None,
            "baseline_metrics": baseline_metrics,
        },
        critical_classes=sorted(set(critical_classes or [])),
    )
    session.add(model)
    session.flush()
    relative_path = f"empresa_{company_id}/model_{model.id}.joblib"
    path = model_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".joblib.tmp")
    try:
        engine.pipeline.fit(
            [row["features"] for row in dataset.linhas],
            [row["target_conta_contrapartida"] for row in dataset.linhas],
        )
        joblib.dump(engine.pipeline, temporary)
        model.artifact_sha256 = sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(path)
        model.artifact_path = relative_path
        record_audit_event(
            session,
            event_type="model.candidate_created",
            empresa_id=company_id,
            resource_id=str(model.id),
            metadata={"manifest_id": model.manifest_id, "evaluation_method": evaluation["method"]},
        )
        session.flush()
        return model
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def active_version(session: Session, company_id: int) -> ModelVersion | None:
    return session.scalar(
        select(ModelVersion).where(
            ModelVersion.empresa_id == company_id,
            ModelVersion.status == "active",
        )
    )


def _verify_artifact(model: ModelVersion, model_dir: Path) -> None:
    expected = f"empresa_{model.empresa_id}/model_{model.id}.joblib"
    if model.artifact_path != expected:
        raise ModelLifecycleError("Caminho do artefato invalido")
    path = model_dir / expected
    if not path.is_file() or sha256(path.read_bytes()).hexdigest() != model.artifact_sha256:
        raise ModelLifecycleError("Artefato ausente ou alterado")


def _check_guardrails(candidate: ModelVersion, active: ModelVersion | None) -> None:
    if not candidate.evaluation.get("valid") or not candidate.metrics:
        raise ModelLifecycleError("Avaliacao insuficiente para promocao")
    candidate_classes = candidate.metrics["per_class_f1"]
    checked = candidate.critical_classes or [int(key) for key in candidate_classes]
    for label in checked:
        if str(label) not in candidate_classes:
            raise ModelLifecycleError("Classe critica sem avaliacao")
    if active is None:
        if candidate.evaluation.get("comparison_version_id") is not None:
            raise ModelLifecycleError("Avaliacao desatualizada em relacao ao ativo")
        return
    if candidate.evaluation.get("comparison_version_id") != active.id:
        raise ModelLifecycleError("Avaliacao desatualizada em relacao ao ativo")
    baseline = candidate.evaluation.get("baseline_metrics")
    if not baseline:
        raise ModelLifecycleError("Avaliacao do ativo ausente")
    if candidate.metrics["macro_f1"] + 1e-12 < baseline["macro_f1"]:
        raise ModelLifecycleError("Regressao de macro F1")
    active_classes = baseline["per_class_f1"]
    for label in checked:
        key = str(label)
        if key in active_classes and candidate_classes[key] + 1e-12 < active_classes[key]:
            raise ModelLifecycleError("Regressao em classe critica")


def change_active_version(
    session: Session,
    *,
    company_id: int,
    version_id: int,
    model_dir: Path | str,
    rollback: bool = False,
) -> ModelVersion:
    """Serialize lifecycle changes on the company row and audit the switch."""
    company = session.scalar(
        select(Empresa).where(Empresa.id == company_id).with_for_update()
    )
    if company is None:
        raise ModelLifecycleError("Empresa nao encontrada")
    target = session.get(ModelVersion, version_id)
    if target is None or target.empresa_id != company_id:
        raise ModelLifecycleError("Versao nao encontrada para a empresa")
    expected_status = "retired" if rollback else "candidate"
    if target.status != expected_status:
        raise ModelLifecycleError("Estado da versao nao permite esta acao")
    current = active_version(session, company_id)
    _verify_artifact(target, Path(model_dir))
    if not rollback:
        _check_guardrails(target, current)
    elif not target.evaluation.get("valid"):
        raise ModelLifecycleError("Versao anterior sem avaliacao valida")
    previous_id = current.id if current else None
    if current is not None:
        current.status = "retired"
        session.flush()
    target.status = "active"
    session.flush()
    record_audit_event(
        session,
        event_type="model.rolled_back" if rollback else "model.promoted",
        empresa_id=company_id,
        resource_id=str(target.id),
        metadata={"previous_version_id": previous_id, "version_id": target.id},
    )
    return target
