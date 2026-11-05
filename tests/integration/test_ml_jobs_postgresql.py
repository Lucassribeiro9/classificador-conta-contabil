"""Real PostgreSQL concurrency and recovery for ML jobs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from core.ml_jobs import claim_next_ml_job, enqueue_ml_job
from core.ml_worker import MLWorker
from core.models import AuditEvent, Empresa, MLJob, ModelVersion
from tests.integration.test_postgresql_integration import _postgres_database_url

pytestmark = pytest.mark.integration_postgres


def _cleanup(engine, company_id: int | None):
    if company_id is None:
        return
    with Session(engine) as session:
        session.execute(delete(AuditEvent).where(AuditEvent.empresa_id == company_id))
        session.execute(delete(MLJob).where(MLJob.empresa_id == company_id))
        session.execute(delete(Empresa).where(Empresa.id == company_id))
        session.commit()


def test_two_workers_never_claim_two_jobs_of_one_company():
    engine = create_engine(_postgres_database_url())
    sessions = sessionmaker(bind=engine)
    suffix = uuid4().hex[:10]
    company_id = None
    try:
        with Session(engine) as session:
            company = Empresa(
                nome_empresa=f"ML jobs {suffix}", api_key=f"ml-jobs-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(company)
            session.flush()
            company_id = company.id
            for n in (1, 2):
                enqueue_ml_job(
                    session, company_id=company_id, kind="train",
                    idempotency_key=f"{suffix}-{n}", payload={},
                )
            session.commit()

        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = list(pool.map(
                lambda n: claim_next_ml_job(sessions, worker_id=f"worker-{n}"),
                (1, 2),
            ))
        assert sum(job is not None for job in claimed) == 1
        with Session(engine) as session:
            jobs = session.scalars(select(MLJob).where(MLJob.empresa_id == company_id)).all()
            assert sorted(job.status for job in jobs) == ["queued", "running"]
    finally:
        _cleanup(engine, company_id)
        engine.dispose()


def test_expired_running_job_is_reclaimed_before_older_queued_job():
    engine = create_engine(_postgres_database_url())
    sessions = sessionmaker(bind=engine)
    suffix = uuid4().hex[:10]
    company_id = None
    try:
        with Session(engine) as session:
            company = Empresa(
                nome_empresa=f"ML recovery {suffix}", api_key=f"ml-recovery-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(company)
            session.flush()
            company_id = company.id
            queued = enqueue_ml_job(
                session, company_id=company_id, kind="classify",
                idempotency_key=f"queued-{suffix}", payload={"inputs": []},
            )
            expired = enqueue_ml_job(
                session, company_id=company_id, kind="train",
                idempotency_key=f"expired-{suffix}", payload={},
            )
            expired.status = "running"
            expired.attempts = 1
            expired.lease_token = "old-token"
            expired.lease_owner = "dead-worker"
            expired.lease_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
            session.commit()
            queued_id, expired_id = queued.id, expired.id

        claim = claim_next_ml_job(sessions, worker_id="recovery-worker")
        assert claim is not None and claim.id == expired_id
        with Session(engine) as session:
            assert session.get(MLJob, queued_id).status == "queued"
            assert session.get(MLJob, expired_id).attempts == 2
    finally:
        _cleanup(engine, company_id)
        engine.dispose()


def test_concurrent_replay_returns_one_persisted_job():
    engine = create_engine(_postgres_database_url())
    sessions = sessionmaker(bind=engine)
    suffix = uuid4().hex[:10]
    company_id = None
    try:
        with Session(engine) as session:
            company = Empresa(
                nome_empresa=f"ML replay {suffix}", api_key=f"ml-replay-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(company)
            session.commit()
            company_id = company.id

        barrier = Barrier(2)

        def submit():
            with sessions() as session:
                barrier.wait(timeout=5)
                job = enqueue_ml_job(
                    session, company_id=company_id, kind="classify",
                    idempotency_key=f"replay-{suffix}", payload={"inputs": []},
                )
                job_id = job.id
                session.commit()
                return job_id

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: submit(), (1, 2)))
        assert ids[0] == ids[1]
        with Session(engine) as session:
            assert session.query(MLJob).filter_by(empresa_id=company_id).count() == 1
    finally:
        _cleanup(engine, company_id)
        engine.dispose()


def test_cancel_during_execution_keeps_result_unpublished(tmp_path):
    engine = create_engine(_postgres_database_url())
    sessions = sessionmaker(bind=engine)
    suffix = uuid4().hex[:10]
    company_id = None
    started, release = Event(), Event()
    try:
        with Session(engine) as session:
            company = Empresa(
                nome_empresa=f"ML cancel {suffix}", api_key=f"ml-cancel-{suffix}",
                cnpj_cpf=f"{int(suffix, 16) % 10**14:014d}",
                cod_dominio=int(suffix, 16) % 2_000_000_000,
            )
            session.add(company)
            session.flush()
            job = enqueue_ml_job(
                session, company_id=company.id, kind="classify",
                idempotency_key=f"cancel-{suffix}", payload={"inputs": []},
            )
            job_id = job.id
            company_id = company.id
            session.commit()

        worker = MLWorker(sessions, worker_id="cancel-worker", model_dir=tmp_path)

        def paused_classification(session, job):
            started.set()
            assert release.wait(timeout=10)
            return {"results": ["must_not_publish"]}

        worker._classify = paused_classification
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.run_once)
            assert started.wait(timeout=10)
            with sessions.begin() as session:
                job = session.get(MLJob, job_id)
                assert job.status == "running"
                job.cancel_requested = True
            release.set()
            assert future.result(timeout=10)

        with Session(engine) as session:
            job = session.get(MLJob, job_id)
            assert job.status == "cancelled"
            assert job.result is None
            assert job.lease_token is None
    finally:
        release.set()
        _cleanup(engine, company_id)
        engine.dispose()


def test_cancel_after_training_rolls_back_candidate_and_removes_artifact(tmp_path, monkeypatch):
    from benchmarks.ml_pool import _seed_jobs
    from core import ml_worker as worker_module

    engine = create_engine(_postgres_database_url())
    sessions = sessionmaker(bind=engine)
    started, release = Event(), Event()
    try:
        job_id = _seed_jobs(sessions, count=1, suffix=uuid4().hex[:8])[0]
        with Session(engine) as session:
            company_id = session.get(MLJob, job_id).empresa_id
        real_create_candidate = worker_module.create_candidate

        def paused_candidate(*args, **kwargs):
            version = real_create_candidate(*args, **kwargs)
            started.set()
            assert release.wait(timeout=10)
            return version

        monkeypatch.setattr(worker_module, "create_candidate", paused_candidate)
        worker = MLWorker(sessions, worker_id="cancel-train", model_dir=tmp_path)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.run_once)
            assert started.wait(timeout=10)
            with sessions.begin() as session:
                session.get(MLJob, job_id).cancel_requested = True
            release.set()
            assert future.result(timeout=10)
        with Session(engine) as session:
            assert session.get(MLJob, job_id).status == "cancelled"
            assert session.scalar(select(ModelVersion.id).where(
                ModelVersion.empresa_id == company_id,
            )) is None
        assert not list(tmp_path.rglob("*.joblib"))
    finally:
        release.set()
        engine.dispose()
