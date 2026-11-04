"""Execute ML jobs with a fenced lease and atomic database publication."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread

from sqlalchemy import select, update

from core.audit import record_audit_event
from core.conta_contabil_empresa import garantir_identidade_contabil
from core.dataset_builder import build_dataset_treino_contrapartida
from core.ml_engine import ClassificadorContabil
from core.ml_jobs import ClaimedMLJob, claim_next_ml_job
from core.model_versions import create_candidate
from core.models import Empresa, MLJob
from core.movimentos_operacionais_classification import (
    MovimentoOperacionalModelNotFound,
    classificar_movimentos_operacionais_pendentes,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobCancelled(Exception):
    pass


class LeaseLost(Exception):
    pass


DETERMINISTIC_ERRORS = {"insufficient_dataset", "model_not_found", "invalid_predicted_account", "unknown_job_kind"}


class MLWorker:
    def __init__(self, sessions, *, worker_id: str, model_dir: str | Path,
                 lease_seconds: int = 600, max_attempts: int = 2):
        self.sessions = sessions
        self.worker_id = worker_id
        self.model_dir = Path(model_dir)
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts

    def renew_lease(self, claim: ClaimedMLJob) -> bool:
        with self.sessions.begin() as session:
            result = session.execute(update(MLJob).where(
                MLJob.id == claim.id, MLJob.status == "running",
                MLJob.lease_token == claim.lease_token,
            ).values(lease_expires_at=_now() + timedelta(seconds=self.lease_seconds)))
            return result.rowcount == 1

    def run_once(self) -> bool:
        claim = claim_next_ml_job(
            self.sessions, worker_id=self.worker_id,
            lease_seconds=self.lease_seconds, max_attempts=self.max_attempts,
        )
        if claim is None:
            return False
        if claim.kind == "classify":
            with self.sessions.begin() as session:
                job = session.get(MLJob, claim.id)
                record_audit_event(session, event_type="classification.started",
                                   user_id=job.requested_by, empresa_id=claim.company_id,
                                   resource_id="ml_classification",
                                   metadata={"total_solicitado": len(job.payload["inputs"])})
        stop = Event()
        heartbeat = Thread(target=self._heartbeat, args=(claim, stop), daemon=True)
        heartbeat.start()
        try:
            self._execute(claim)
        except JobCancelled:
            self._finish_failure(claim, "cancelled")
        except LeaseLost:
            pass
        except MovimentoOperacionalModelNotFound:
            self._finish_failure(claim, "model_not_found", retryable=False)
        except ValueError as exc:
            code = str(exc)
            self._finish_failure(claim, code if code in DETERMINISTIC_ERRORS else "processing_error",
                                 retryable=code not in DETERMINISTIC_ERRORS)
        except Exception:
            self._finish_failure(claim, "processing_error")
        finally:
            stop.set()
            heartbeat.join()
        return True

    def _heartbeat(self, claim: ClaimedMLJob, stop: Event) -> None:
        while not stop.wait(max(1, self.lease_seconds // 3)):
            if not self.renew_lease(claim):
                return

    def _execute(self, claim: ClaimedMLJob) -> None:
        artifact_path: Path | None = None
        try:
            with self.sessions.begin() as session:
                job = session.get(MLJob, claim.id)
                if job is None or job.lease_token != claim.lease_token:
                    raise LeaseLost()
                if job.cancel_requested:
                    raise JobCancelled()
                if job.kind == "train":
                    dataset = build_dataset_treino_contrapartida(session, empresa_id=claim.company_id)
                    if not dataset.metadata.get("treinavel", False):
                        raise ValueError("insufficient_dataset")
                    company = session.get(Empresa, claim.company_id)
                    version = create_candidate(
                        session, dataset, model_dir=self.model_dir,
                        critical_classes=company.ml_critical_classes,
                    )
                    artifact_path = self.model_dir / version.artifact_path
                    result = {"version_id": version.id, "status": "candidate",
                              "empresa_id": claim.company_id,
                              "total_linhas": dataset.metadata["total_linhas"],
                              "total_descartes": dataset.metadata["total_descartes"],
                              "contagem_por_target": dataset.metadata["contagem_por_target"],
                              "treinavel": dataset.metadata["treinavel"]}
                elif job.kind == "classify":
                    result = self._classify(session, job)
                elif job.kind == "classify_movements":
                    result = classificar_movimentos_operacionais_pendentes(
                        session, empresa_id=claim.company_id, model_dir=self.model_dir,
                        movement_ids=job.payload["movement_ids"],
                    )
                else:
                    raise ValueError("unknown_job_kind")
                session.refresh(job, with_for_update=True)
                if job.lease_token != claim.lease_token or job.status != "running":
                    raise LeaseLost()
                if job.cancel_requested:
                    raise JobCancelled()
                job.result = result
                job.status = "completed"
                job.progress = 100
                job.lease_token = None
                job.lease_owner = None
                job.lease_expires_at = None
                record_audit_event(session, event_type="ml.job.completed",
                                   user_id=job.requested_by, empresa_id=claim.company_id, resource_id=str(job.id),
                                   metadata={"kind": job.kind, "attempt": claim.attempt})
        except Exception:
            if artifact_path is not None:
                artifact_path.unlink(missing_ok=True)
            raise

    def _classify(self, session, job: MLJob) -> dict:
        engine = ClassificadorContabil(session, model_dir=self.model_dir)
        if not engine.model_exists_for_company(job.empresa_id):
            raise ValueError("model_not_found")
        predictions = engine.classify_lancamentos_from_saved_model(
            empresa_id=job.empresa_id, lancamentos=job.payload["inputs"],
        )
        for code in {item["conta_contrapartida"] for item in predictions}:
            account = garantir_identidade_contabil(
                session, empresa_id=job.empresa_id, codigo=code,
            )
            if account is None or not account.is_classificavel:
                raise ValueError("invalid_predicted_account")
        version_id = engine.active_model_version_id_for_company(job.empresa_id)
        record_audit_event(session, event_type="classification.completed",
                           user_id=job.requested_by, empresa_id=job.empresa_id, resource_id="ml_classification",
                           metadata={"total_processado": len(predictions),
                                     "total_revisao": sum(1 for p in predictions if p["needs_review"]),
                                     **({"model_version_id": version_id} if version_id else {})})
        return {"empresa_id": job.empresa_id, "quantidade_processada": len(predictions),
                "results": predictions, "model_version_id": version_id}

    def _finish_failure(self, claim: ClaimedMLJob, code: str, *, retryable: bool = True) -> None:
        with self.sessions.begin() as session:
            job = session.scalar(select(MLJob).where(
                MLJob.id == claim.id, MLJob.lease_token == claim.lease_token,
                MLJob.status == "running",
            ).with_for_update())
            if job is None:
                return
            if code == "cancelled" or job.cancel_requested:
                job.status = "cancelled"
                job.error_code = None
            else:
                job.status = "queued" if retryable and job.attempts < self.max_attempts else "failed"
                job.error_code = code if job.status == "failed" else None
                if job.status == "queued":
                    job.progress = 0
            job.lease_token = None
            job.lease_owner = None
            job.lease_expires_at = None
            job.result = None
            record_audit_event(session, event_type="ml.job.failed" if job.status == "failed" else "ml.job.retried",
                               user_id=job.requested_by, empresa_id=claim.company_id, resource_id=str(job.id),
                               metadata={"kind": job.kind, "attempt": claim.attempt,
                                         "error_code": code})
            if job.kind == "classify" and job.status == "failed":
                record_audit_event(session, event_type="classification.failed",
                                   user_id=job.requested_by, empresa_id=claim.company_id, resource_id="ml_classification",
                                   metadata={"reason": code, "error_type": "ModelNotFound" if code == "model_not_found" else code,
                                             "total_solicitado": len(job.payload["inputs"])})
            if job.kind == "classify_movements" and job.status == "failed":
                record_audit_event(session, event_type="operational_movements.classification_failed",
                                   user_id=job.requested_by, empresa_id=claim.company_id,
                                   resource_id="operational_movements_classification",
                                   metadata={"total_pendentes": len(job.payload["movement_ids"]),
                                             "error_type": "ModelNotFound" if code == "model_not_found" else code,
                                             "reason": code})
