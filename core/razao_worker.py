"""Worker transacional da fila durável de importações do Razão."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from typing import BinaryIO, Callable
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from core.audit import record_audit_event
from core.models import LoteImportacaoRazao, TentativaImportacaoRazao
from core.razao_storage import TemporaryFileUnavailable


class JobError(Exception):
    def __init__(self, code: str, message: str, request_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.request_id = request_id


class TransientJobError(JobError):
    """Falha técnica que admite uma repetição automática."""


class DeterministicJobError(JobError):
    """Falha de entrada ou regra que não deve ser repetida automaticamente."""


class LeaseLost(RuntimeError):
    """O worker não pode confirmar resultados depois de perder a posse."""


@dataclass(frozen=True)
class ClaimedJob:
    lote_id: int
    empresa_id: int
    attempt: int
    lease_token: str


@dataclass(frozen=True)
class JobResult:
    total_linhas: int
    total_importadas: int
    total_invalidas: int
    warnings_total: int
    warnings_metadata: dict
    status: str | None = None


Processor = Callable[[Session, ClaimedJob, BinaryIO, Callable[..., None]], JobResult]


def process_razao_upload(
    session: Session,
    claim: ClaimedJob,
    stream: BinaryIO,
    progress: Callable[..., None],
) -> JobResult:
    """Adapta o importador existente à transação controlada pelo worker."""
    from core.razao_importer import RazaoImportError, import_razao
    from core.razao_parser import RazaoParseError

    lote = session.get(LoteImportacaoRazao, claim.lote_id)
    if lote is None:
        raise DeterministicJobError("batch_not_found", "Lote de importação não encontrado.")
    try:
        summary = import_razao(
            session,
            stream,
            empresa_id=lote.empresa_id,
            usuario_id=lote.usuario_id,
            original_filename=lote.original_filename,
            existing_lote=lote,
            progress=progress,
        )
    except (RazaoParseError, RazaoImportError, ValueError) as exc:
        raise DeterministicJobError(
            "invalid_ledger", "Arquivo do Razão inválido."
        ) from exc
    return JobResult(
        total_linhas=summary.total_linhas,
        total_importadas=summary.total_importadas,
        total_invalidas=summary.total_invalidas,
        warnings_total=summary.warnings_total,
        warnings_metadata=summary.warnings_metadata or {"totals_by_code": {}},
        status=summary.status,
    )


class _Heartbeat:
    def __init__(self, worker: "RazaoWorker", claim: ClaimedJob):
        self.worker = worker
        self.claim = claim
        self.stop_event = Event()
        self.lost = Event()
        self.thread = Thread(target=self._run, name=f"razao-heartbeat-{claim.lote_id}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=max(self.worker.heartbeat_seconds * 2, 1))

    def _run(self) -> None:
        while not self.stop_event.wait(self.worker.heartbeat_seconds):
            try:
                if not self.worker.renew_lease(self.claim):
                    self.lost.set()
                    return
            except Exception:
                self.lost.set()
                return


class RazaoWorker:
    """Adquire, executa e finaliza uma tentativa sem controlar o processo HTTP."""

    def __init__(
        self,
        sessions,
        storage,
        processor: Processor,
        *,
        worker_id: str,
        lease_seconds: int = 600,
        heartbeat_seconds: float = 30,
        clock: Callable[[], datetime] | None = None,
    ):
        if lease_seconds <= 0 or heartbeat_seconds <= 0 or not worker_id:
            raise ValueError("Configuração do worker inválida.")
        self.sessions = sessions
        self.storage = storage
        self.processor = processor
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run_once(self) -> bool:
        recovered = self._fail_exhausted_expired()
        claim = self.claim_next()
        if claim is None:
            return recovered

        heartbeat = _Heartbeat(self, claim)
        try:
            with self.storage.open_for_job(claim.lote_id) as stream:
                heartbeat.start()
                try:
                    with self.sessions.begin() as session:
                        result = self.processor(
                            session,
                            claim,
                            stream,
                            lambda **values: self.update_progress(claim, **values),
                        )
                        heartbeat.stop()
                        if heartbeat.lost.is_set():
                            raise LeaseLost("Lease perdida durante o processamento.")
                        self._complete(session, claim, result)
                except LeaseLost:
                    raise
                except JobError:
                    raise
                except Exception as exc:
                    raise TransientJobError(
                        "processing_failed", "Falha temporária no processamento."
                    ) from exc
        except LeaseLost:
            heartbeat.stop()
            raise
        except TemporaryFileUnavailable as exc:
            heartbeat.stop()
            self._fail(
                claim,
                DeterministicJobError(exc.code, str(exc)),
            )
        except JobError as exc:
            heartbeat.stop()
            self._fail(claim, exc)
        else:
            self.storage.cleanup()
        return True

    def _fail_exhausted_expired(self) -> bool:
        """Encerra lease expirada quando as duas tentativas já foram usadas."""
        now = self.clock()
        with self.sessions.begin() as session:
            lote = session.scalar(
                select(LoteImportacaoRazao)
                .where(
                    LoteImportacaoRazao.status == "processing",
                    LoteImportacaoRazao.lease_expires_at <= now,
                    LoteImportacaoRazao.attempt_count >= 2,
                )
                .order_by(LoteImportacaoRazao.created_at, LoteImportacaoRazao.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if lote is None:
                return False
            lote.status = "failed"
            lote.lease_token = None
            lote.lease_owner = None
            lote.lease_expires_at = None
            lote.error_code = "lease_expired"
            lote.error_message = "O processamento perdeu a posse do lote."
            lote.failed_at = now
            attempt = session.scalar(
                select(TentativaImportacaoRazao).where(
                    TentativaImportacaoRazao.lote_id == lote.id,
                    TentativaImportacaoRazao.numero == lote.attempt_count,
                )
            )
            if attempt is not None and attempt.finished_at is None:
                attempt.finished_at = now
                attempt.resultado = "failed"
                attempt.error_code = "lease_expired"
                attempt.error_message = "O processamento perdeu a posse do lote."
            record_audit_event(
                session,
                event_type="razao.job.failed",
                empresa_id=lote.empresa_id,
                resource_id=str(lote.id),
                metadata={"attempt": lote.attempt_count, "error_code": "lease_expired"},
            )
            return True

    def claim_next(self) -> ClaimedJob | None:
        now = self.clock()
        with self.sessions.begin() as session:
            lote = session.scalar(
                select(LoteImportacaoRazao)
                .where(
                    or_(
                        LoteImportacaoRazao.status == "queued",
                        and_(
                            LoteImportacaoRazao.status == "processing",
                            LoteImportacaoRazao.lease_expires_at <= now,
                        ),
                    ),
                    LoteImportacaoRazao.attempt_count < 2,
                )
                .order_by(LoteImportacaoRazao.created_at, LoteImportacaoRazao.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if lote is None:
                return None

            if lote.status == "processing":
                previous = session.scalar(
                    select(TentativaImportacaoRazao).where(
                        TentativaImportacaoRazao.lote_id == lote.id,
                        TentativaImportacaoRazao.numero == lote.attempt_count,
                    )
                )
                if previous is not None and previous.finished_at is None:
                    previous.finished_at = now
                    previous.resultado = "interrupted"
                record_audit_event(
                    session,
                    event_type="razao.job.retried",
                    empresa_id=lote.empresa_id,
                    resource_id=str(lote.id),
                    metadata={"attempt": lote.attempt_count + 1, "reason": "lease_expired"},
                )

            lote.attempt_count += 1
            token = str(uuid4())
            lote.status = "processing"
            lote.lease_token = token
            lote.lease_owner = self.worker_id
            lote.heartbeat_at = now
            lote.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
            lote.total_linhas = None
            lote.linhas_processadas = 0
            lote.total_importadas = 0
            lote.total_invalidas = 0
            lote.warnings_total = 0
            lote.warnings_metadata = {"totals_by_code": {}}
            lote.error_code = None
            lote.error_message = None
            lote.error_request_id = None
            lote.failed_at = None
            session.add(
                TentativaImportacaoRazao(
                    lote_id=lote.id,
                    numero=lote.attempt_count,
                    started_at=now,
                )
            )
            record_audit_event(
                session,
                event_type="razao.job.started",
                empresa_id=lote.empresa_id,
                resource_id=str(lote.id),
                metadata={"attempt": lote.attempt_count},
            )
            return ClaimedJob(lote.id, lote.empresa_id, lote.attempt_count, token)

    def renew_lease(self, claim: ClaimedJob) -> bool:
        now = self.clock()
        with self.sessions.begin() as session:
            result = session.execute(
                update(LoteImportacaoRazao)
                .where(
                    LoteImportacaoRazao.id == claim.lote_id,
                    LoteImportacaoRazao.status == "processing",
                    LoteImportacaoRazao.lease_token == claim.lease_token,
                )
                .values(
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=self.lease_seconds),
                )
            )
            return result.rowcount == 1

    def update_progress(self, claim: ClaimedJob, **values) -> None:
        allowed = {
            "total_linhas",
            "linhas_processadas",
            "total_importadas",
            "total_invalidas",
            "warnings_total",
        }
        if not values or set(values) - allowed:
            raise ValueError("Campos de progresso inválidos.")
        with self.sessions.begin() as session:
            result = session.execute(
                update(LoteImportacaoRazao)
                .where(
                    LoteImportacaoRazao.id == claim.lote_id,
                    LoteImportacaoRazao.status == "processing",
                    LoteImportacaoRazao.lease_token == claim.lease_token,
                )
                .values(**values)
            )
            if result.rowcount != 1:
                raise LeaseLost("Lease perdida ao atualizar progresso.")

    def _complete(self, session: Session, claim: ClaimedJob, result: JobResult) -> None:
        lote = self._locked_owned_lote(session, claim)
        status = result.status or (
            "completed_with_warnings" if result.warnings_total else "completed"
        )
        if status not in {"completed", "completed_with_warnings", "failed"}:
            raise ValueError("Resultado inválido do processador do Razão.")
        lote.status = status
        lote.total_linhas = result.total_linhas
        lote.linhas_processadas = result.total_linhas
        lote.total_importadas = result.total_importadas
        lote.total_invalidas = result.total_invalidas
        lote.warnings_total = result.warnings_total
        lote.warnings_metadata = result.warnings_metadata
        lote.lease_token = None
        lote.lease_owner = None
        lote.lease_expires_at = None
        if status == "failed":
            lote.error_code = "invalid_ledger"
            lote.error_message = "Nenhum lançamento válido foi encontrado."
            lote.failed_at = self.clock()
        attempt = self._attempt(session, claim)
        attempt.finished_at = self.clock()
        attempt.resultado = status
        record_audit_event(
            session,
            event_type="razao.job.failed" if status == "failed" else "razao.job.completed",
            empresa_id=lote.empresa_id,
            resource_id=str(lote.id),
            metadata={"attempt": claim.attempt, "status": status},
        )

    def _fail(self, claim: ClaimedJob, error: JobError) -> None:
        now = self.clock()
        with self.sessions.begin() as session:
            lote = self._locked_owned_lote(session, claim)
            retry = isinstance(error, TransientJobError) and claim.attempt < 2
            lote.status = "queued" if retry else "failed"
            lote.lease_token = None
            lote.lease_owner = None
            lote.lease_expires_at = None
            lote.error_code = error.code
            lote.error_message = error.safe_message
            lote.error_request_id = error.request_id
            lote.failed_at = None if retry else now
            attempt = self._attempt(session, claim)
            attempt.finished_at = now
            attempt.resultado = "interrupted" if retry else "failed"
            attempt.error_code = error.code
            attempt.error_message = error.safe_message
            attempt.error_request_id = error.request_id
            record_audit_event(
                session,
                event_type="razao.job.retried" if retry else "razao.job.failed",
                empresa_id=lote.empresa_id,
                resource_id=str(lote.id),
                metadata={"attempt": claim.attempt, "error_code": error.code},
            )

    @staticmethod
    def _attempt(session: Session, claim: ClaimedJob) -> TentativaImportacaoRazao:
        return session.scalar(
            select(TentativaImportacaoRazao).where(
                TentativaImportacaoRazao.lote_id == claim.lote_id,
                TentativaImportacaoRazao.numero == claim.attempt,
            )
        )

    @staticmethod
    def _locked_owned_lote(session: Session, claim: ClaimedJob) -> LoteImportacaoRazao:
        lote = session.scalar(
            select(LoteImportacaoRazao)
            .where(
                LoteImportacaoRazao.id == claim.lote_id,
                LoteImportacaoRazao.status == "processing",
                LoteImportacaoRazao.lease_token == claim.lease_token,
            )
            .with_for_update()
        )
        if lote is None:
            raise LeaseLost("Lease perdida antes da confirmação.")
        return lote


def build_workers(sessions, storage, processor, *, worker_id: str, settings):
    """Cria a quantidade configurada de consumidores da mesma fila durável."""
    return [
        RazaoWorker(
            sessions,
            storage,
            processor,
            worker_id=f"{worker_id}-{index + 1}",
            lease_seconds=settings.RAZAO_LEASE_SECONDS,
            heartbeat_seconds=settings.RAZAO_HEARTBEAT_SECONDS,
        )
        for index in range(settings.RAZAO_WORKER_CONCURRENCY)
    ]
