from pathlib import Path

from agent_runner import (
    ContextValidation,
    ExecutionStatus,
    RunnerAction,
    RunnerRequest,
    RunnerService,
    RunnerStore,
    StageResult,
    StageResultStatus,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = 1_000.0

    def now(self) -> float:
        return self.current


class FakeContextValidator:
    def __init__(self, result: ContextValidation = ContextValidation.VALID) -> None:
        self.result = result

    def validate(self, request: RunnerRequest) -> ContextValidation:
        return self.result


class FakeExecutor:
    def __init__(self, *results: StageResult) -> None:
        self.results = list(results)
        self.requests: list[RunnerRequest] = []

    def run(self, request: RunnerRequest, execution) -> StageResult:
        self.requests.append(request)
        return self.results.pop(0)

    def request_cancel(self, execution_id: str) -> None:
        pass


def _request(
    event_id: str = "00000000-0000-4000-8000-000000000001",
    issue_number: int = 375,
    payload: dict | None = None,
) -> RunnerRequest:
    return RunnerRequest(
        event_id=event_id,
        action=RunnerAction.IMPLEMENT,
        repository="Lucassribeiro9/classificador-conta-contabil",
        issue_number=issue_number,
        expected_state="agent:ready-to-implement",
        payload=payload
        or {
            "base_branch": "main",
            "base_sha": "21ce85f",
            "approved_branch": "feat/agent-runner-core",
            "task_review_ref": "conversation:task-review-375",
        },
    )


def test_implement_valid_issue_persists_sanitized_checkpoint_and_status(tmp_path: Path):
    store = RunnerStore(tmp_path / "runner.sqlite3")
    service = RunnerService(
        store=store,
        context_validator=FakeContextValidator(),
        executor=FakeExecutor(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="EXECUTION_COMPLETED",
                sanitized_summary="Draft ready without sensitive content.",
                head_sha="6c6fb22",
            )
        ),
        clock=FakeClock(),
    )

    response = service.handle(_request())

    assert response.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert response.code == "EXECUTION_COMPLETED"
    assert response.retryable is False
    assert response.execution_id

    status = service.handle(
        RunnerRequest(
            event_id="00000000-0000-4000-8000-000000000002",
            action=RunnerAction.STATUS,
            repository="Lucassribeiro9/classificador-conta-contabil",
            issue_number=375,
            expected_state="agent:running",
            payload={"execution_id": response.execution_id},
        )
    )

    assert status.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert status.execution_id == response.execution_id
    assert status.checkpoint is not None
    assert status.checkpoint.stage == "draft"
    assert status.checkpoint.status == "completed"
    assert status.checkpoint.result_code == "EXECUTION_COMPLETED"
    assert status.checkpoint.sanitized_summary == "Draft ready without sensitive content."
    assert not hasattr(status.checkpoint, "prompt")
    assert not hasattr(status.checkpoint, "diff")


def test_event_id_is_idempotent_and_rejects_payload_conflict(tmp_path: Path):
    executor = FakeExecutor(
        StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="First response.",
        )
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )
    request = _request(event_id="00000000-0000-4000-8000-000000000010")

    first = service.handle(request)
    repeated = service.handle(request)
    conflict = service.handle(
        _request(
            event_id=request.event_id,
            payload={
                **request.payload,
                "base_sha": "different-sha",
            },
        )
    )

    assert first.execution_id == repeated.execution_id
    assert first.code == repeated.code
    assert len(executor.requests) == 1
    assert conflict.code == "EVENT_PAYLOAD_CONFLICT"
    assert conflict.status == ExecutionStatus.BLOCKED


def test_payload_with_forbidden_field_is_rejected_before_execution(tmp_path: Path):
    executor = FakeExecutor(
        StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="Should not run.",
        )
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )

    response = service.handle(
        _request(payload={**_request().payload, "prompt": "do something"})
    )

    assert response.code == "ACTION_NOT_ALLOWED"
    assert response.status == ExecutionStatus.BLOCKED
    assert response.execution_id is None
    assert executor.requests == []


class FakeRepairingExecutor(FakeExecutor):
    def __init__(self, run_result: StageResult, repair_result: StageResult) -> None:
        super().__init__(run_result)
        self.repair_result = repair_result
        self.repair_calls = 0

    def repair_mechanical_failure(self, request: RunnerRequest, execution) -> StageResult:
        self.repair_calls += 1
        return self.repair_result


def test_single_mechanical_failure_runs_one_injected_repair(tmp_path: Path):
    executor = FakeRepairingExecutor(
        StageResult(
            status=StageResultStatus.MECHANICAL_FAILURE,
            code="MECHANICAL_FAILURE",
            sanitized_summary="git diff check failed.",
        ),
        StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="Mechanical issue fixed.",
            head_sha="fixed-sha",
        ),
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )

    response = service.handle(_request(event_id="00000000-0000-4000-8000-000000000020"))

    assert response.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert response.code == "EXECUTION_COMPLETED"
    assert executor.repair_calls == 1
    assert response.checkpoint is not None
    assert response.checkpoint.attempt == 2
    assert response.checkpoint.sanitized_summary == "Mechanical issue fixed."


def test_second_mechanical_failure_blocks_without_another_repair(tmp_path: Path):
    executor = FakeRepairingExecutor(
        StageResult(
            status=StageResultStatus.MECHANICAL_FAILURE,
            code="MECHANICAL_FAILURE",
            sanitized_summary="First mechanical failure.",
        ),
        StageResult(
            status=StageResultStatus.MECHANICAL_FAILURE,
            code="MECHANICAL_FAILURE",
            sanitized_summary="Second mechanical failure.",
        ),
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )

    response = service.handle(_request(event_id="00000000-0000-4000-8000-000000000021"))

    assert response.status == ExecutionStatus.BLOCKED
    assert response.code == "MECHANICAL_FAILURE"
    assert executor.repair_calls == 1
    assert response.checkpoint is not None
    assert response.checkpoint.status == "blocked"
    assert response.checkpoint.attempt == 2


class SlowExecutor(FakeExecutor):
    def __init__(self, clock: FakeClock) -> None:
        super().__init__(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="EXECUTION_COMPLETED",
                sanitized_summary="Finished too late.",
            )
        )
        self.clock = clock

    def run(self, request: RunnerRequest, execution) -> StageResult:
        self.clock.current += 1_801
        return super().run(request, execution)


def test_timeout_blocks_execution_and_preserves_checkpoint(tmp_path: Path):
    clock = FakeClock()
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=SlowExecutor(clock),
        clock=clock,
        timeout_seconds=1_800,
    )

    response = service.handle(_request(event_id="00000000-0000-4000-8000-000000000030"))

    assert response.status == ExecutionStatus.BLOCKED
    assert response.code == "EXECUTION_BLOCKED"
    assert response.checkpoint is not None
    assert response.checkpoint.status == "blocked"
    assert response.checkpoint.result_code == "EXECUTION_TIMED_OUT"
    assert response.checkpoint.sanitized_summary == "Execution timed out."


class RecordingCancelExecutor(FakeExecutor):
    def __init__(self) -> None:
        super().__init__()
        self.cancelled: list[str] = []

    def request_cancel(self, execution_id: str) -> None:
        self.cancelled.append(execution_id)


def test_cancel_active_execution_preserves_checkpoint_and_releases_locks(tmp_path: Path):
    store = RunnerStore(tmp_path / "runner.sqlite3")
    request = _request(event_id="00000000-0000-4000-8000-000000000040")
    execution = store.create_execution_with_locks(request, now=1_000.0)
    assert not isinstance(execution, str)
    executor = RecordingCancelExecutor()
    service = RunnerService(
        store=store,
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )

    response = service.handle(
        RunnerRequest(
            event_id="00000000-0000-4000-8000-000000000041",
            action=RunnerAction.CANCEL,
            repository=request.repository,
            issue_number=request.issue_number,
            expected_state="agent:running",
            payload={"execution_id": execution.execution_id},
        )
    )

    assert response.status == ExecutionStatus.CANCELLED
    assert response.code == "EXECUTION_CANCELLED"
    assert executor.cancelled == [execution.execution_id]
    assert response.checkpoint is not None
    assert response.checkpoint.status == "cancelled"
    assert response.checkpoint.sanitized_summary == "Execution cancelled by request."

    next_execution = store.create_execution_with_locks(
        _request(event_id="00000000-0000-4000-8000-000000000042"),
        now=1_001.0,
    )
    assert not isinstance(next_execution, str)


def test_resume_blocked_execution_with_new_event_and_checkpoint_ref(tmp_path: Path):
    executor = FakeExecutor(
        StageResult(
            status=StageResultStatus.NEW_DECISION_REQUIRED,
            code="NEW_DECISION_REQUIRED",
            sanitized_summary="Decision required.",
        ),
        StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="Resumed successfully.",
            head_sha="resumed-sha",
        ),
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )

    blocked = service.handle(_request(event_id="00000000-0000-4000-8000-000000000050"))
    assert blocked.status == ExecutionStatus.BLOCKED
    assert blocked.checkpoint is not None

    resumed = service.handle(
        RunnerRequest(
            event_id="00000000-0000-4000-8000-000000000051",
            action=RunnerAction.RESUME,
            repository="Lucassribeiro9/classificador-conta-contabil",
            issue_number=375,
            expected_state="agent:blocked",
            payload={
                "execution_id": blocked.execution_id,
                "checkpoint_ref": str(blocked.checkpoint.id),
            },
        )
    )

    assert resumed.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert resumed.code == "EXECUTION_COMPLETED"
    assert resumed.execution_id == blocked.execution_id
    assert resumed.checkpoint is not None
    assert resumed.checkpoint.previous_checkpoint_id == blocked.checkpoint.id
    assert len(executor.requests) == 2


class ReentrantExecutor(FakeExecutor):
    def __init__(self) -> None:
        super().__init__(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="EXECUTION_COMPLETED",
                sanitized_summary="Outer execution completed.",
            )
        )
        self.inner_response = None
        self.service: RunnerService | None = None

    def run(self, request: RunnerRequest, execution) -> StageResult:
        assert self.service is not None
        self.inner_response = self.service.handle(
            _request(
                event_id="00000000-0000-4000-8000-000000000061",
                issue_number=376,
            )
        )
        return super().run(request, execution)


def test_global_lock_rejects_concurrent_implement_without_duplicate_work(tmp_path: Path):
    executor = ReentrantExecutor()
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=executor,
        clock=FakeClock(),
    )
    executor.service = service

    response = service.handle(_request(event_id="00000000-0000-4000-8000-000000000060"))

    assert response.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert executor.inner_response is not None
    assert executor.inner_response.status == ExecutionStatus.BLOCKED
    assert executor.inner_response.code == "PILOT_CAPACITY_REACHED"
    assert len(executor.requests) == 1


def test_context_validation_failure_blocks_before_executor(tmp_path: Path):
    executor = FakeExecutor(
        StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="Should not run.",
        )
    )
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(ContextValidation.STATE_MISMATCH),
        executor=executor,
        clock=FakeClock(),
    )

    response = service.handle(_request(event_id="00000000-0000-4000-8000-000000000070"))

    assert response.status == ExecutionStatus.BLOCKED
    assert response.code == "STATE_MISMATCH"
    assert response.execution_id is None
    assert executor.requests == []


def test_runner_store_persists_private_interface_nonce_replay(tmp_path: Path):
    store = RunnerStore(tmp_path / "runner.sqlite3")

    first = store.register_nonce("primary", "nonce-377", "2026-08-05T12:00:00Z")
    replay = store.register_nonce("primary", "nonce-377", "2026-08-05T12:00:00Z")
    other_key = store.register_nonce("secondary", "nonce-377", "2026-08-05T12:00:00Z")

    assert first is True
    assert replay is False
    assert other_key is True
