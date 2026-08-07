from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from agent_runner.telemetria import TelemetryRecorder


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
    def __init__(self, result: StageResult) -> None:
        self.result = result
        self.requests: list[RunnerRequest] = []

    def run(self, request: RunnerRequest, execution) -> StageResult:
        self.requests.append(request)
        return self.result

    def repair_mechanical_failure(self, request: RunnerRequest, execution) -> StageResult:
        raise AssertionError("repair should not run in telemetry tests")

    def request_cancel(self, execution_id: str) -> None:
        pass


class FakeRepairingExecutor(FakeExecutor):
    def __init__(self) -> None:
        super().__init__(
            StageResult(
                status=StageResultStatus.MECHANICAL_FAILURE,
                code="MECHANICAL_FAILURE",
                sanitized_summary="Mechanical failure.",
            )
        )

    def repair_mechanical_failure(self, request: RunnerRequest, execution) -> StageResult:
        return StageResult(
            status=StageResultStatus.COMPLETED,
            code="EXECUTION_COMPLETED",
            sanitized_summary="Mechanical issue fixed.",
        )


class FailingTelemetryRecorder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record_event(self, event: dict, *, now: datetime | None = None):
        self.calls.append(event)
        raise RuntimeError("private telemetry storage unavailable")


def _request(
    *,
    event_id: str = "00000000-0000-4000-8000-000000000380",
    payload: dict | None = None,
) -> RunnerRequest:
    return RunnerRequest(
        event_id=event_id,
        action=RunnerAction.IMPLEMENT,
        repository="Lucassribeiro9/classificador-conta-contabil",
        issue_number=380,
        expected_state="agent:ready-to-implement",
        payload=payload
        or {
            "base_branch": "main",
            "base_sha": "21ce85f",
            "approved_branch": "feat/agent-telemetria-privada",
            "task_review_ref": "conversation:task-review-380",
        },
    )


def _rows(db_path: Path, table: str) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        return list(connection.execute(f"SELECT * FROM {table} ORDER BY id"))


def test_enabled_private_telemetry_persists_only_allowed_operational_fields(tmp_path: Path):
    db_path = tmp_path / "private" / "telemetry.sqlite3"
    recorder = TelemetryRecorder(db_path)

    result = recorder.record_event(
        {
            "event_id": "evt-1",
            "execution_id": "exec-1",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
            "issue_number": 380,
            "stage": "start",
            "command_category": "implement",
            "started_at": "2026-08-07T12:00:00+00:00",
            "finished_at": "2026-08-07T12:00:02+00:00",
            "duration_ms": 2_000,
            "result": "running",
            "attempts": 1,
            "code": "EXECUTION_STARTED",
            "input_units": 10,
            "output_units": 20,
            "total_units": 30,
            "estimated_cost_cents": 4,
            "technical_ref": "issue-380",
        },
        now=datetime(2026, 8, 7, 12, 0, tzinfo=UTC),
    )

    assert result.recorded is True
    rows = _rows(db_path, "telemetry_events")
    assert len(rows) == 1
    assert dict(rows[0]) == {
        "id": 1,
        "event_id": "evt-1",
        "execution_id": "exec-1",
        "repository": "Lucassribeiro9/classificador-conta-contabil",
        "issue_number": 380,
        "stage": "start",
        "command_category": "implement",
        "started_at": "2026-08-07T12:00:00+00:00",
        "finished_at": "2026-08-07T12:00:02+00:00",
        "duration_ms": 2_000,
        "result": "running",
        "attempts": 1,
        "code": "EXECUTION_STARTED",
        "input_units": 10,
        "output_units": 20,
        "total_units": 30,
        "estimated_cost_cents": 4,
        "technical_ref": "issue-380",
        "created_at": "2026-08-07T12:00:00+00:00",
    }


@pytest.mark.parametrize("forbidden_field", ["prompt", "raw_log", "diff", "accounting_data"])
def test_telemetry_rejects_entire_event_when_forbidden_content_is_present(
    tmp_path: Path, forbidden_field: str
):
    db_path = tmp_path / "telemetry.sqlite3"
    recorder = TelemetryRecorder(db_path)

    result = recorder.record_event(
        {
            "event_id": "evt-forbidden",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
            "issue_number": 380,
            "stage": "start",
            "result": "blocked",
            forbidden_field: "conteudo privado",
        },
        now=datetime(2026, 8, 7, 12, 0, tzinfo=UTC),
    )

    assert result.recorded is False
    assert result.code == "TELEMETRY_REJECTED_FORBIDDEN_CONTENT"
    assert _rows(db_path, "telemetry_events") == []


def test_telemetry_is_disabled_when_private_db_path_is_absent(tmp_path: Path):
    recorder = TelemetryRecorder.from_env({})

    result = recorder.record_event(
        {
            "event_id": "evt-disabled",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
            "issue_number": 380,
            "stage": "start",
            "result": "running",
        },
        now=datetime(2026, 8, 7, 12, 0, tzinfo=UTC),
    )

    assert result.recorded is False
    assert result.code == "TELEMETRY_DISABLED"
    assert list(tmp_path.iterdir()) == []


def test_telemetry_aggregates_and_prunes_details_older_than_90_days(tmp_path: Path):
    db_path = tmp_path / "telemetry.sqlite3"
    recorder = TelemetryRecorder(db_path)
    recorder.record_event(
        {
            "event_id": "old-1",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
            "issue_number": 380,
            "stage": "delivery",
            "command_category": "implement",
            "duration_ms": 100,
            "result": "blocked",
            "attempts": 2,
            "code": "EXECUTION_BLOCKED",
            "total_units": 50,
            "estimated_cost_cents": 7,
        },
        now=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
    )
    recorder.record_event(
        {
            "event_id": "recent-1",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
            "issue_number": 380,
            "stage": "delivery",
            "command_category": "implement",
            "duration_ms": 200,
            "result": "completed",
            "attempts": 1,
            "code": "EXECUTION_COMPLETED",
        },
        now=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
    )

    result = recorder.aggregate_and_prune(now=datetime(2026, 8, 7, 12, 0, tzinfo=UTC))

    assert result.recorded is True
    remaining = _rows(db_path, "telemetry_events")
    assert [row["event_id"] for row in remaining] == ["recent-1"]
    aggregates = _rows(db_path, "telemetry_monthly_aggregates")
    assert len(aggregates) == 1
    assert aggregates[0]["month"] == "2026-04"
    assert aggregates[0]["executions_count"] == 1
    assert aggregates[0]["attempts_total"] == 2
    assert aggregates[0]["duration_ms_total"] == 100
    assert aggregates[0]["total_units_total"] == 50
    assert aggregates[0]["estimated_cost_cents_total"] == 7


def test_runner_records_start_and_final_telemetry_without_leaking_payload(tmp_path: Path):
    telemetry_db = tmp_path / "telemetry.sqlite3"
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=FakeExecutor(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="EXECUTION_COMPLETED",
                sanitized_summary="Draft ready.",
            )
        ),
        clock=FakeClock(),
        telemetry=TelemetryRecorder(telemetry_db),
    )

    response = service.handle(_request())

    assert response.status == ExecutionStatus.AWAITING_MANUAL_TEST
    rows = _rows(telemetry_db, "telemetry_events")
    assert [row["stage"] for row in rows] == ["start", "draft"]
    assert [row["result"] for row in rows] == ["running", "awaiting_manual_test"]
    persisted = [dict(row) for row in rows]
    assert all("approved_branch" not in str(row) for row in persisted)
    assert all("task_review_ref" not in str(row) for row in persisted)


def test_telemetry_failure_does_not_change_runner_response_or_state(tmp_path: Path):
    telemetry = FailingTelemetryRecorder()
    service = RunnerService(
        store=RunnerStore(tmp_path / "runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=FakeExecutor(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="EXECUTION_COMPLETED",
                sanitized_summary="Draft ready.",
            )
        ),
        clock=FakeClock(),
        telemetry=telemetry,
    )

    response = service.handle(_request())

    assert response.status == ExecutionStatus.AWAITING_MANUAL_TEST
    assert response.code == "EXECUTION_COMPLETED"
    assert response.execution_id is not None
    assert len(telemetry.calls) == 2


def test_runner_records_block_before_execution_and_mechanical_correction(tmp_path: Path):
    blocked_db = tmp_path / "blocked.sqlite3"
    blocked_service = RunnerService(
        store=RunnerStore(tmp_path / "blocked-runner.sqlite3"),
        context_validator=FakeContextValidator(ContextValidation.APPROVAL_REQUIRED),
        executor=FakeExecutor(
            StageResult(
                status=StageResultStatus.COMPLETED,
                code="SHOULD_NOT_RUN",
                sanitized_summary="Should not run.",
            )
        ),
        clock=FakeClock(),
        telemetry=TelemetryRecorder(blocked_db),
    )

    blocked = blocked_service.handle(_request(event_id="00000000-0000-4000-8000-000000000381"))

    assert blocked.code == "APPROVAL_REQUIRED"
    blocked_rows = _rows(blocked_db, "telemetry_events")
    assert [(row["stage"], row["result"], row["code"]) for row in blocked_rows] == [
        ("rejection", "blocked", "APPROVAL_REQUIRED")
    ]

    correction_db = tmp_path / "correction.sqlite3"
    correction_service = RunnerService(
        store=RunnerStore(tmp_path / "correction-runner.sqlite3"),
        context_validator=FakeContextValidator(),
        executor=FakeRepairingExecutor(),
        clock=FakeClock(),
        telemetry=TelemetryRecorder(correction_db),
    )

    fixed = correction_service.handle(_request(event_id="00000000-0000-4000-8000-000000000382"))

    assert fixed.code == "EXECUTION_COMPLETED"
    correction_rows = _rows(correction_db, "telemetry_events")
    assert [(row["stage"], row["result"], row["code"]) for row in correction_rows] == [
        ("start", "running", "EXECUTION_STARTED"),
        ("correction", "running", "MECHANICAL_REPAIR_STARTED"),
        ("draft", "awaiting_manual_test", "EXECUTION_COMPLETED"),
    ]
