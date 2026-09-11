from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    TentativaImportacaoRazao,
    Usuario,
)
from core.razao_worker import (
    DeterministicJobError,
    JobResult,
    LeaseLost,
    RazaoWorker,
    TransientJobError,
    build_workers,
    process_razao_upload,
)


class FakeStorage:
    def __init__(self):
        self.cleaned = 0

    class _Open:
        def __enter__(self):
            return object()

        def __exit__(self, *_):
            return False

    def open_for_job(self, _lote_id):
        return self._Open()

    def cleanup(self):
        self.cleaned += 1


@pytest.fixture
def worker_context(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions.begin() as session:
        empresa = Empresa(
            nome_empresa="Empresa",
            cnpj_cpf="11222333000144",
            api_key="key",
            cod_dominio=480,
        )
        usuario = Usuario(nome="Operador", login="worker-user", email="worker@example.com",
                          senha_hash="hash", papel="operador")
        session.add_all(
            [
                empresa,
                usuario,
                ContaContabil(codigo=10046, classificacao="1.1", nome="Origem", tipo="A", grau=6),
                    ContaContabil(codigo=20001, classificacao="2.1", nome="Destino", tipo="S", grau=6),
            ]
        )
        session.flush()
        lote = LoteImportacaoRazao(
            empresa_id=empresa.id, usuario_id=usuario.id, original_filename="razao.xlsx",
            file_hash="sha256:worker", status="queued",
        )
        session.add(lote)
        session.flush()
        lote_id = lote.id
    yield sessions, lote_id
    engine.dispose()


def test_worker_completes_job_in_one_business_transaction_and_audits(worker_context):
    sessions, lote_id = worker_context
    storage = FakeStorage()

    def process(session, claim, _stream, progress):
        progress(total_linhas=2, linhas_processadas=1, total_importadas=1, total_invalidas=0)
        assert session.get(LoteImportacaoRazao, claim.lote_id).status == "processing"
        return JobResult(total_linhas=2, total_importadas=2, total_invalidas=0,
                         warnings_total=0, warnings_metadata={"totals_by_code": {}})

    worker = RazaoWorker(sessions, storage, process, worker_id="worker-1")

    assert worker.run_once() is True
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "completed"
        assert lote.attempt_count == 1
        assert lote.lease_token is None
        assert lote.total_importadas == 2
        tentativa = session.scalar(select(TentativaImportacaoRazao))
        assert tentativa.resultado == "completed"
        assert [event.event_type for event in session.scalars(select(AuditEvent))] == [
            "razao.job.started", "razao.job.completed"
        ]
    assert storage.cleaned == 1


@pytest.mark.parametrize(
    "error,expected_status,expected_result",
    [
        (TransientJobError("database_unavailable", "Falha temporária."), "queued", "interrupted"),
        (DeterministicJobError("invalid_layout", "Arquivo inválido.", "req-1"), "failed", "failed"),
    ],
)
def test_worker_rolls_back_and_classifies_failures(
    worker_context, error, expected_status, expected_result
):
    sessions, lote_id = worker_context

    def process(session, _claim, _stream, _progress):
        session.get(LoteImportacaoRazao, lote_id).warnings_metadata = {"should": "rollback"}
        raise error

    worker = RazaoWorker(sessions, FakeStorage(), process, worker_id="worker-1")

    assert worker.run_once() is True
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == expected_status
        assert lote.warnings_metadata == {"totals_by_code": {}}
        assert lote.error_code == error.code
        tentativa = session.scalar(select(TentativaImportacaoRazao))
        assert tentativa.resultado == expected_result


def test_second_transient_failure_finishes_job(worker_context):
    sessions, lote_id = worker_context

    def fail(*_args):
        raise TransientJobError("database_unavailable", "Falha temporária.")

    worker = RazaoWorker(sessions, FakeStorage(), fail, worker_id="worker-1")
    assert worker.run_once() is True
    assert worker.run_once() is True

    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "failed"
        assert lote.attempt_count == 2
        assert [attempt.resultado for attempt in lote.tentativas] == ["interrupted", "failed"]


def test_manual_retry_after_two_attempts_is_claimed_as_third_attempt(worker_context):
    sessions, lote_id = worker_context
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with sessions.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.attempt_count = 2
        session.add_all(
            [
                TentativaImportacaoRazao(
                    lote_id=lote_id,
                    numero=1,
                    started_at=now,
                    finished_at=now,
                    resultado="interrupted",
                ),
                TentativaImportacaoRazao(
                    lote_id=lote_id,
                    numero=2,
                    started_at=now,
                    finished_at=now,
                    resultado="failed",
                ),
            ]
        )

    worker = RazaoWorker(
        sessions,
        FakeStorage(),
        lambda *_: JobResult(1, 1, 0, 0, {"totals_by_code": {}}),
        worker_id="worker-manual-retry",
        clock=lambda: now,
    )

    assert worker.run_once() is True
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "completed"
        assert lote.attempt_count == 3
        assert [attempt.resultado for attempt in lote.tentativas] == [
            "interrupted",
            "failed",
            "completed",
        ]


def test_expired_lease_is_recovered_and_previous_attempt_interrupted(worker_context):
    sessions, lote_id = worker_context
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with sessions.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "processing"
        lote.attempt_count = 1
        lote.lease_token = "old-token"
        lote.lease_owner = "dead-worker"
        lote.lease_expires_at = now - timedelta(seconds=1)
        lote.heartbeat_at = now - timedelta(minutes=11)
        session.add(TentativaImportacaoRazao(lote_id=lote_id, numero=1, started_at=now))

    worker = RazaoWorker(
        sessions, FakeStorage(),
        lambda *_: JobResult(1, 1, 0, 0, {"totals_by_code": {}}),
        worker_id="worker-2", clock=lambda: now,
    )

    assert worker.run_once() is True
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "completed"
        assert lote.attempt_count == 2
        assert [attempt.resultado for attempt in lote.tentativas] == ["interrupted", "completed"]


def test_second_expired_lease_finishes_job_without_new_attempt(worker_context):
    sessions, lote_id = worker_context
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with sessions.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = "processing"
        lote.attempt_count = 2
        lote.lease_token = "expired-token"
        lote.lease_owner = "dead-worker"
        lote.lease_expires_at = now - timedelta(seconds=1)
        session.add(
            TentativaImportacaoRazao(lote_id=lote_id, numero=2, started_at=now)
        )

    worker = RazaoWorker(
        sessions, FakeStorage(), lambda *_: pytest.fail("não deve processar"),
        worker_id="worker-3", clock=lambda: now,
    )

    assert worker.run_once() is True
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "failed"
        assert lote.attempt_count == 2
        assert lote.error_code == "lease_expired"
        assert lote.tentativas[0].resultado == "failed"


def test_lost_lease_rolls_back_business_results(worker_context):
    sessions, lote_id = worker_context

    def steal_lease(session, claim, _stream, _progress):
        session.get(LoteImportacaoRazao, lote_id).warnings_metadata = {"should": "rollback"}
        with sessions.begin() as other:
            lote = other.get(LoteImportacaoRazao, lote_id)
            lote.lease_token = "new-owner-token"
        return JobResult(1, 1, 0, 0, {"totals_by_code": {}})

    worker = RazaoWorker(sessions, FakeStorage(), steal_lease, worker_id="worker-1")

    with pytest.raises(LeaseLost):
        worker.run_once()
    with sessions() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        assert lote.status == "processing"
        assert lote.warnings_metadata == {"totals_by_code": {}}


def test_default_processor_reuses_claimed_lote_and_reports_progress(
    worker_context, monkeypatch
):
    from io import BytesIO
    from core import razao_importer

    sessions, lote_id = worker_context
    parsed = [{
        "bloco_id": "bloco:1", "data": "2026-01-02", "numero": "1",
        "historico": "Lançamento", "conta_origem": "10046",
        "contrapartida": "20001", "debito": "10.00", "credito": None,
    }]
    monkeypatch.setattr(
        razao_importer, "_parse_lancamentos_and_validate_company", lambda *_: parsed
    )
    progress = []
    claim = type("Claim", (), {
        "lote_id": lote_id, "empresa_id": 1, "attempt": 1, "lease_token": "token"
    })()

    with sessions.begin() as session:
        result = process_razao_upload(
            session, claim, BytesIO(b"xlsx"), lambda **values: progress.append(values)
        )

    assert result.total_importadas == 1
    assert progress[-1]["linhas_processadas"] == 1
    with sessions() as session:
        assert session.query(LoteImportacaoRazao).count() == 1
        assert session.query(LancamentoRazaoNormalizado).count() == 1


def test_worker_pool_uses_validated_runtime_configuration(worker_context):
    sessions, _ = worker_context

    class Config:
        RAZAO_WORKER_CONCURRENCY = 2
        RAZAO_HEARTBEAT_SECONDS = 30
        RAZAO_LEASE_SECONDS = 600

    workers = build_workers(
        sessions, FakeStorage(), lambda *_: None, worker_id="worker", settings=Config
    )

    assert [worker.worker_id for worker in workers] == ["worker-1", "worker-2"]
    assert all(worker.heartbeat_seconds == 30 for worker in workers)
    assert all(worker.lease_seconds == 600 for worker in workers)


def test_worker_configuration_defaults_and_environment(monkeypatch):
    from core.config import Settings

    defaults = Settings(_env_file=None)
    assert defaults.RAZAO_WORKER_CONCURRENCY == 1
    assert defaults.RAZAO_HEARTBEAT_SECONDS == 30
    assert defaults.RAZAO_LEASE_SECONDS == 600

    monkeypatch.setenv("RAZAO_WORKER_CONCURRENCY", "2")
    monkeypatch.setenv("RAZAO_HEARTBEAT_SECONDS", "15")
    monkeypatch.setenv("RAZAO_LEASE_SECONDS", "300")
    configured = Settings(_env_file=None)
    assert configured.RAZAO_WORKER_CONCURRENCY == 2
    assert configured.RAZAO_HEARTBEAT_SECONDS == 15
    assert configured.RAZAO_LEASE_SECONDS == 300
