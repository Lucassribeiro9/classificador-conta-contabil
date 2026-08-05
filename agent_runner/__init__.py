from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class RunnerAction(StrEnum):
    IMPLEMENT = "implement"
    RESUME = "resume"
    CANCEL = "cancel"
    STATUS = "status"


class ExecutionStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    AWAITING_MANUAL_TEST = "awaiting_manual_test"


class ContextValidation(StrEnum):
    VALID = "valid"
    APPROVAL_REQUIRED = "approval_required"
    STATE_MISMATCH = "state_mismatch"
    NOT_ALLOWED = "not_allowed"
    BLOCKED_DEPENDENCY = "blocked_dependency"
    CONFLICTING_PR = "conflicting_pr"


class StageResultStatus(StrEnum):
    COMPLETED = "completed"
    DRAFT_CREATED = "draft_created"
    BLOCKED = "blocked"
    NEW_DECISION_REQUIRED = "new_decision_required"
    MECHANICAL_FAILURE = "mechanical_failure"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RunnerRequest:
    event_id: str
    action: RunnerAction
    repository: str
    issue_number: int
    expected_state: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StageResult:
    status: StageResultStatus
    code: str
    sanitized_summary: str
    head_sha: str | None = None


@dataclass(frozen=True)
class Checkpoint:
    id: int
    execution_id: str
    issue_number: int
    stage: str
    status: str
    attempt: int
    event_id: str
    previous_checkpoint_id: int | None
    created_at: float
    base_sha: str | None
    head_sha: str | None
    result_code: str
    sanitized_summary: str


@dataclass(frozen=True)
class Execution:
    execution_id: str
    issue_number: int
    status: ExecutionStatus
    event_id: str
    base_sha: str | None
    head_sha: str | None
    mechanical_fix_attempts: int
    cancel_requested: bool


@dataclass(frozen=True)
class RunnerResponse:
    event_id: str
    execution_id: str | None
    action: RunnerAction
    status: ExecutionStatus
    code: str
    message: str
    retryable: bool
    checkpoint: Checkpoint | None = None


class Clock(Protocol):
    def now(self) -> float: ...


class ContextValidator(Protocol):
    def validate(self, request: RunnerRequest) -> ContextValidation: ...


class StageExecutor(Protocol):
    def run(self, request: RunnerRequest, execution: Execution) -> StageResult: ...

    def repair_mechanical_failure(
        self, request: RunnerRequest, execution: Execution
    ) -> StageResult: ...

    def request_cancel(self, execution_id: str) -> None: ...


class RunnerStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    issue_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    base_sha TEXT,
                    head_sha TEXT,
                    mechanical_fix_attempts INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    started_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    issue_number INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    previous_checkpoint_id INTEGER,
                    created_at REAL NOT NULL,
                    base_sha TEXT,
                    head_sha TEXT,
                    result_code TEXT NOT NULL,
                    sanitized_summary TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS locks (
                    lock_name TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS nonces (
                    key_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (key_id, nonce)
                );
                """
            )

    def get_event_response(self, event_id: str, payload_hash: str) -> RunnerResponse | str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_hash, response_json FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        if row["payload_hash"] != payload_hash:
            return "conflict"
        return _response_from_json(json.loads(row["response_json"]))

    def persist_event_response(
        self,
        event_id: str,
        payload_hash: str,
        response: RunnerResponse,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events (event_id, payload_hash, response_json)
                VALUES (?, ?, ?)
                """,
                (event_id, payload_hash, json.dumps(_response_to_json(response), sort_keys=True)),
            )

    def register_nonce(self, key_id: str, nonce: str, timestamp: str) -> bool:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO nonces (key_id, nonce, timestamp)
                    VALUES (?, ?, ?)
                    """,
                    (key_id, nonce, timestamp),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def create_execution_with_locks(
        self,
        request: RunnerRequest,
        now: float,
    ) -> Execution | str:
        execution_id = str(uuid.uuid4())
        base_sha = request.payload.get("base_sha")
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                active_global = connection.execute(
                    "SELECT execution_id FROM locks WHERE lock_name = 'global'"
                ).fetchone()
                if active_global is not None:
                    return "PILOT_CAPACITY_REACHED"
                issue_lock_name = f"issue:{request.issue_number}"
                active_issue = connection.execute(
                    "SELECT execution_id FROM locks WHERE lock_name = ?",
                    (issue_lock_name,),
                ).fetchone()
                if active_issue is not None:
                    return "ISSUE_ALREADY_RUNNING"
                execution = Execution(
                    execution_id=execution_id,
                    issue_number=request.issue_number,
                    status=ExecutionStatus.RUNNING,
                    event_id=request.event_id,
                    base_sha=base_sha,
                    head_sha=None,
                    mechanical_fix_attempts=0,
                    cancel_requested=False,
                )
                connection.execute(
                    """
                    INSERT INTO executions (
                        execution_id, issue_number, status, event_id, base_sha,
                        head_sha, mechanical_fix_attempts, cancel_requested,
                        started_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        execution.execution_id,
                        execution.issue_number,
                        execution.status.value,
                        execution.event_id,
                        execution.base_sha,
                        execution.head_sha,
                        execution.mechanical_fix_attempts,
                        int(execution.cancel_requested),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    "INSERT INTO locks (lock_name, execution_id) VALUES ('global', ?)",
                    (execution_id,),
                )
                connection.execute(
                    "INSERT INTO locks (lock_name, execution_id) VALUES (?, ?)",
                    (issue_lock_name, execution_id),
                )
                connection.commit()
                return execution
            except Exception:
                connection.rollback()
                raise

    def update_execution(
        self,
        execution_id: str,
        *,
        status: ExecutionStatus,
        now: float,
        head_sha: str | None = None,
        release_locks: bool = False,
        mechanical_fix_attempts: int | None = None,
    ) -> Execution:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE executions
                SET status = ?,
                    head_sha = COALESCE(?, head_sha),
                    mechanical_fix_attempts = COALESCE(?, mechanical_fix_attempts),
                    updated_at = ?
                WHERE execution_id = ?
                """,
                (status.value, head_sha, mechanical_fix_attempts, now, execution_id),
            )
            if release_locks:
                connection.execute(
                    "DELETE FROM locks WHERE execution_id = ?",
                    (execution_id,),
                )
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        return _execution_from_row(row)

    def add_checkpoint(
        self,
        execution: Execution,
        *,
        stage: str,
        status: str,
        event_id: str,
        result_code: str,
        sanitized_summary: str,
        created_at: float,
        head_sha: str | None,
    ) -> Checkpoint:
        previous = self.latest_checkpoint(execution.execution_id)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO checkpoints (
                    execution_id, issue_number, stage, status, attempt, event_id,
                    previous_checkpoint_id, created_at, base_sha, head_sha,
                    result_code, sanitized_summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution.execution_id,
                    execution.issue_number,
                    stage,
                    status,
                    execution.mechanical_fix_attempts + 1,
                    event_id,
                    previous.id if previous else None,
                    created_at,
                    execution.base_sha,
                    head_sha,
                    result_code,
                    _sanitize_summary(sanitized_summary),
                ),
            )
            checkpoint_id = int(cursor.lastrowid)
        checkpoint = self.latest_checkpoint(execution.execution_id)
        assert checkpoint is not None
        assert checkpoint.id == checkpoint_id
        return checkpoint

    def latest_checkpoint(self, execution_id: str) -> Checkpoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM checkpoints
                WHERE execution_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (execution_id,),
            ).fetchone()
        return _checkpoint_from_row(row) if row else None

    def get_execution(self, execution_id: str) -> Execution | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
        return _execution_from_row(row) if row else None

    def get_latest_execution_for_issue(self, issue_number: int) -> Execution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM executions
                WHERE issue_number = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (issue_number,),
            ).fetchone()
        return _execution_from_row(row) if row else None


FORBIDDEN_PAYLOAD_FIELDS = {"command", "script", "shell", "prompt", "secret", "accounting_data", "diff"}
ALLOWED_PAYLOAD_FIELDS = {
    RunnerAction.IMPLEMENT: {"base_branch", "base_sha", "approved_branch", "task_review_ref"},
    RunnerAction.RESUME: {"execution_id", "checkpoint_ref"},
    RunnerAction.CANCEL: {"execution_id"},
    RunnerAction.STATUS: {"execution_id"},
}


class RunnerService:
    def __init__(
        self,
        *,
        store: RunnerStore,
        context_validator: ContextValidator,
        executor: StageExecutor,
        clock: Clock,
        timeout_seconds: int = 1_800,
    ) -> None:
        self.store = store
        self.context_validator = context_validator
        self.executor = executor
        self.clock = clock
        self.timeout_seconds = timeout_seconds

    def handle(self, request: RunnerRequest) -> RunnerResponse:
        if not _payload_allowed(request):
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="ACTION_NOT_ALLOWED",
                message="Payload contains unknown or forbidden fields.",
                retryable=False,
            )

        payload_hash = _payload_hash(request)
        existing = self.store.get_event_response(request.event_id, payload_hash)
        if existing == "conflict":
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="EVENT_PAYLOAD_CONFLICT",
                message="Event id already used with a different payload.",
                retryable=False,
            )
        if isinstance(existing, RunnerResponse):
            return existing

        if request.action == RunnerAction.IMPLEMENT:
            response = self._implement(request)
        elif request.action == RunnerAction.RESUME:
            response = self._resume(request)
        elif request.action == RunnerAction.CANCEL:
            response = self._cancel(request)
        elif request.action == RunnerAction.STATUS:
            response = self._status(request)
        else:
            response = RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="ACTION_NOT_ALLOWED",
                message="Action is not implemented by the runner core yet.",
                retryable=False,
            )

        self.store.persist_event_response(request.event_id, payload_hash, response)
        return response

    def _implement(self, request: RunnerRequest) -> RunnerResponse:
        validation = self.context_validator.validate(request)
        if validation != ContextValidation.VALID:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code=_validation_code(validation),
                message="Context validation failed.",
                retryable=False,
            )

        started_at = self.clock.now()
        execution_or_code = self.store.create_execution_with_locks(request, started_at)
        if isinstance(execution_or_code, str):
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code=execution_or_code,
                message="Execution lock is not available.",
                retryable=False,
            )

        execution = execution_or_code
        result = self.executor.run(request, execution)
        if (
            result.status == StageResultStatus.MECHANICAL_FAILURE
            and execution.mechanical_fix_attempts == 0
        ):
            execution = self.store.update_execution(
                execution.execution_id,
                status=ExecutionStatus.RUNNING,
                now=self.clock.now(),
                mechanical_fix_attempts=1,
            )
            result = self.executor.repair_mechanical_failure(request, execution)

        timed_out = self.clock.now() - started_at > self.timeout_seconds
        if timed_out:
            result = StageResult(
                status=StageResultStatus.BLOCKED,
                code="EXECUTION_TIMED_OUT",
                sanitized_summary="Execution timed out.",
                head_sha=result.head_sha,
            )

        final_status = (
            ExecutionStatus.AWAITING_MANUAL_TEST
            if result.status in {StageResultStatus.COMPLETED, StageResultStatus.DRAFT_CREATED}
            else ExecutionStatus.BLOCKED
        )
        updated = self.store.update_execution(
            execution.execution_id,
            status=final_status,
            now=self.clock.now(),
            head_sha=result.head_sha,
            release_locks=True,
            mechanical_fix_attempts=execution.mechanical_fix_attempts,
        )
        checkpoint = self.store.add_checkpoint(
            updated,
            stage="draft" if final_status == ExecutionStatus.AWAITING_MANUAL_TEST else "delivery",
            status="completed" if final_status == ExecutionStatus.AWAITING_MANUAL_TEST else "blocked",
            event_id=request.event_id,
            result_code=result.code,
            sanitized_summary=result.sanitized_summary,
            created_at=self.clock.now(),
            head_sha=result.head_sha,
        )
        return RunnerResponse(
            event_id=request.event_id,
            execution_id=execution.execution_id,
            action=request.action,
            status=final_status,
            code="EXECUTION_BLOCKED" if timed_out else result.code,
            message=result.sanitized_summary,
            retryable=False,
            checkpoint=checkpoint,
        )

    def _resume(self, request: RunnerRequest) -> RunnerResponse:
        execution_id = request.payload.get("execution_id")
        checkpoint_ref = request.payload.get("checkpoint_ref")
        execution = self.store.get_execution(execution_id) if execution_id else None
        if execution is None or execution.status != ExecutionStatus.BLOCKED:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=execution_id,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="EXECUTION_NOT_FOUND",
                message="Blocked execution was not found.",
                retryable=False,
            )
        checkpoint = self.store.latest_checkpoint(execution.execution_id)
        if checkpoint is None or str(checkpoint.id) != str(checkpoint_ref):
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=execution.execution_id,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="ACTION_NOT_ALLOWED",
                message="Checkpoint reference is not compatible.",
                retryable=False,
            )
        validation = self.context_validator.validate(request)
        if validation != ContextValidation.VALID:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=execution.execution_id,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code=_validation_code(validation),
                message="Context validation failed.",
                retryable=False,
            )
        lock_code = _acquire_existing_locks(self.store, execution)
        if lock_code is not None:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=execution.execution_id,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code=lock_code,
                message="Execution lock is not available.",
                retryable=False,
            )
        running = self.store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.RUNNING,
            now=self.clock.now(),
        )
        result = self.executor.run(request, running)
        final_status = (
            ExecutionStatus.AWAITING_MANUAL_TEST
            if result.status in {StageResultStatus.COMPLETED, StageResultStatus.DRAFT_CREATED}
            else ExecutionStatus.BLOCKED
        )
        updated = self.store.update_execution(
            execution.execution_id,
            status=final_status,
            now=self.clock.now(),
            head_sha=result.head_sha,
            release_locks=True,
        )
        new_checkpoint = self.store.add_checkpoint(
            updated,
            stage="draft" if final_status == ExecutionStatus.AWAITING_MANUAL_TEST else "delivery",
            status="completed" if final_status == ExecutionStatus.AWAITING_MANUAL_TEST else "blocked",
            event_id=request.event_id,
            result_code=result.code,
            sanitized_summary=result.sanitized_summary,
            created_at=self.clock.now(),
            head_sha=result.head_sha,
        )
        return RunnerResponse(
            event_id=request.event_id,
            execution_id=execution.execution_id,
            action=request.action,
            status=final_status,
            code=result.code,
            message=result.sanitized_summary,
            retryable=False,
            checkpoint=new_checkpoint,
        )

    def _cancel(self, request: RunnerRequest) -> RunnerResponse:
        execution_id = request.payload.get("execution_id")
        execution = self.store.get_execution(execution_id) if execution_id else None
        if execution is None:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="EXECUTION_NOT_FOUND",
                message="Execution was not found.",
                retryable=False,
            )
        self.executor.request_cancel(execution.execution_id)
        updated = self.store.update_execution(
            execution.execution_id,
            status=ExecutionStatus.CANCELLED,
            now=self.clock.now(),
            release_locks=True,
        )
        checkpoint = self.store.add_checkpoint(
            updated,
            stage="delivery",
            status="cancelled",
            event_id=request.event_id,
            result_code="EXECUTION_CANCELLED",
            sanitized_summary="Execution cancelled by request.",
            created_at=self.clock.now(),
            head_sha=updated.head_sha,
        )
        return RunnerResponse(
            event_id=request.event_id,
            execution_id=execution.execution_id,
            action=request.action,
            status=ExecutionStatus.CANCELLED,
            code="EXECUTION_CANCELLED",
            message="Execution cancelled by request.",
            retryable=False,
            checkpoint=checkpoint,
        )

    def _status(self, request: RunnerRequest) -> RunnerResponse:
        execution_id = request.payload.get("execution_id")
        execution = (
            self.store.get_execution(execution_id)
            if execution_id
            else self.store.get_latest_execution_for_issue(request.issue_number)
        )
        if execution is None:
            return RunnerResponse(
                event_id=request.event_id,
                execution_id=None,
                action=request.action,
                status=ExecutionStatus.BLOCKED,
                code="EXECUTION_NOT_FOUND",
                message="Execution was not found.",
                retryable=False,
            )
        checkpoint = self.store.latest_checkpoint(execution.execution_id)
        return RunnerResponse(
            event_id=request.event_id,
            execution_id=execution.execution_id,
            action=request.action,
            status=execution.status,
            code=checkpoint.result_code if checkpoint else "EXECUTION_STATUS",
            message=checkpoint.sanitized_summary if checkpoint else "Execution status.",
            retryable=False,
            checkpoint=checkpoint,
        )


def _payload_hash(request: RunnerRequest) -> str:
    data = {
        "action": request.action.value,
        "repository": request.repository,
        "issue_number": request.issue_number,
        "expected_state": request.expected_state,
        "payload": request.payload,
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sanitize_summary(value: str) -> str:
    forbidden = ("prompt", "diff", "secret", "token", "accounting_data", "raw_log")
    lowered = value.lower()
    if any(item in lowered for item in forbidden):
        return "Sanitized summary withheld."
    return value


def _validation_code(validation: ContextValidation) -> str:
    return {
        ContextValidation.APPROVAL_REQUIRED: "APPROVAL_REQUIRED",
        ContextValidation.STATE_MISMATCH: "STATE_MISMATCH",
        ContextValidation.NOT_ALLOWED: "ACTION_NOT_ALLOWED",
        ContextValidation.BLOCKED_DEPENDENCY: "EXECUTION_BLOCKED",
        ContextValidation.CONFLICTING_PR: "EXECUTION_BLOCKED",
    }[validation]


def _execution_from_row(row: sqlite3.Row) -> Execution:
    return Execution(
        execution_id=row["execution_id"],
        issue_number=row["issue_number"],
        status=ExecutionStatus(row["status"]),
        event_id=row["event_id"],
        base_sha=row["base_sha"],
        head_sha=row["head_sha"],
        mechanical_fix_attempts=row["mechanical_fix_attempts"],
        cancel_requested=bool(row["cancel_requested"]),
    )


def _checkpoint_from_row(row: sqlite3.Row) -> Checkpoint:
    return Checkpoint(
        id=row["id"],
        execution_id=row["execution_id"],
        issue_number=row["issue_number"],
        stage=row["stage"],
        status=row["status"],
        attempt=row["attempt"],
        event_id=row["event_id"],
        previous_checkpoint_id=row["previous_checkpoint_id"],
        created_at=row["created_at"],
        base_sha=row["base_sha"],
        head_sha=row["head_sha"],
        result_code=row["result_code"],
        sanitized_summary=row["sanitized_summary"],
    )


def _response_to_json(response: RunnerResponse) -> dict[str, Any]:
    return {
        "event_id": response.event_id,
        "execution_id": response.execution_id,
        "action": response.action.value,
        "status": response.status.value,
        "code": response.code,
        "message": response.message,
        "retryable": response.retryable,
        "checkpoint": response.checkpoint.__dict__ if response.checkpoint else None,
    }


def _response_from_json(data: dict[str, Any]) -> RunnerResponse:
    checkpoint_data = data["checkpoint"]
    return RunnerResponse(
        event_id=data["event_id"],
        execution_id=data["execution_id"],
        action=RunnerAction(data["action"]),
        status=ExecutionStatus(data["status"]),
        code=data["code"],
        message=data["message"],
        retryable=data["retryable"],
        checkpoint=Checkpoint(**checkpoint_data) if checkpoint_data else None,
    )


def _payload_allowed(request: RunnerRequest) -> bool:
    keys = set(request.payload)
    if keys & FORBIDDEN_PAYLOAD_FIELDS:
        return False
    allowed = ALLOWED_PAYLOAD_FIELDS.get(request.action)
    if allowed is None:
        return False
    return keys <= allowed


def _acquire_existing_locks(store: RunnerStore, execution: Execution) -> str | None:
    with store._connect() as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            issue_lock_name = f"issue:{execution.issue_number}"
            for lock_name, code in (
                ("global", "PILOT_CAPACITY_REACHED"),
                (issue_lock_name, "ISSUE_ALREADY_RUNNING"),
            ):
                active = connection.execute(
                    "SELECT execution_id FROM locks WHERE lock_name = ?",
                    (lock_name,),
                ).fetchone()
                if active is not None and active["execution_id"] != execution.execution_id:
                    connection.rollback()
                    return code
            connection.execute(
                "INSERT OR REPLACE INTO locks (lock_name, execution_id) VALUES ('global', ?)",
                (execution.execution_id,),
            )
            connection.execute(
                "INSERT OR REPLACE INTO locks (lock_name, execution_id) VALUES (?, ?)",
                (issue_lock_name, execution.execution_id),
            )
            connection.commit()
            return None
        except Exception:
            connection.rollback()
            raise
