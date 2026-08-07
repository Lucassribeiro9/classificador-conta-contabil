from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping


TELEMETRY_DB_ENV = "AGENT_TELEMETRY_DB_PATH"

ALLOWED_EVENT_FIELDS = {
    "event_id",
    "execution_id",
    "repository",
    "issue_number",
    "stage",
    "command_category",
    "started_at",
    "finished_at",
    "duration_ms",
    "result",
    "attempts",
    "code",
    "input_units",
    "output_units",
    "total_units",
    "estimated_cost_cents",
    "technical_ref",
}

FORBIDDEN_EVENT_FIELDS = {
    "accounting_data",
    "content",
    "credential",
    "credentials",
    "diff",
    "file_content",
    "log",
    "logs",
    "private_url",
    "prompt",
    "raw_log",
    "reasoning",
    "response",
    "secret",
    "signature",
    "token",
}


@dataclass(frozen=True)
class TelemetryWriteResult:
    recorded: bool
    code: str
    message: str


class TelemetryRecorder:
    def __init__(self, db_path: Path | str | None) -> None:
        self.db_path = Path(db_path) if db_path else None
        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> TelemetryRecorder:
        source = os.environ if environ is None else environ
        return cls(source.get(TELEMETRY_DB_ENV))

    def record_event(
        self, event: Mapping[str, Any], *, now: datetime | None = None
    ) -> TelemetryWriteResult:
        if self.db_path is None:
            return TelemetryWriteResult(
                recorded=False,
                code="TELEMETRY_DISABLED",
                message="Private telemetry database path is not configured.",
            )

        if _contains_forbidden_content(event):
            self._initialize()
            return TelemetryWriteResult(
                recorded=False,
                code="TELEMETRY_REJECTED_FORBIDDEN_CONTENT",
                message="Telemetry event contains forbidden content.",
            )

        unknown_fields = set(event) - ALLOWED_EVENT_FIELDS
        if unknown_fields:
            return TelemetryWriteResult(
                recorded=False,
                code="TELEMETRY_REJECTED_UNKNOWN_FIELDS",
                message="Telemetry event contains unknown fields.",
            )

        created_at = _iso(now or datetime.now(UTC))
        values = {field: event.get(field) for field in ALLOWED_EVENT_FIELDS}
        values["created_at"] = created_at

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telemetry_events (
                    event_id,
                    execution_id,
                    repository,
                    issue_number,
                    stage,
                    command_category,
                    started_at,
                    finished_at,
                    duration_ms,
                    result,
                    attempts,
                    code,
                    input_units,
                    output_units,
                    total_units,
                    estimated_cost_cents,
                    technical_ref,
                    created_at
                )
                VALUES (
                    :event_id,
                    :execution_id,
                    :repository,
                    :issue_number,
                    :stage,
                    :command_category,
                    :started_at,
                    :finished_at,
                    :duration_ms,
                    :result,
                    :attempts,
                    :code,
                    :input_units,
                    :output_units,
                    :total_units,
                    :estimated_cost_cents,
                    :technical_ref,
                    :created_at
                )
                """,
                values,
            )
        return TelemetryWriteResult(
            recorded=True,
            code="TELEMETRY_RECORDED",
            message="Private telemetry event recorded.",
        )

    def aggregate_and_prune(self, *, now: datetime | None = None) -> TelemetryWriteResult:
        if self.db_path is None:
            return TelemetryWriteResult(
                recorded=False,
                code="TELEMETRY_DISABLED",
                message="Private telemetry database path is not configured.",
            )

        cutoff = _iso((now or datetime.now(UTC)) - timedelta(days=90))
        aggregated_at = _iso(now or datetime.now(UTC))
        with self._connect() as connection:
            expired = list(
                connection.execute(
                    """
                    SELECT
                        substr(created_at, 1, 7) AS month,
                        repository,
                        issue_number,
                        stage,
                        result,
                        code,
                        command_category,
                        count(*) AS executions_count,
                        coalesce(sum(attempts), 0) AS attempts_total,
                        coalesce(sum(duration_ms), 0) AS duration_ms_total,
                        coalesce(sum(input_units), 0) AS input_units_total,
                        coalesce(sum(output_units), 0) AS output_units_total,
                        coalesce(sum(total_units), 0) AS total_units_total,
                        coalesce(sum(estimated_cost_cents), 0) AS estimated_cost_cents_total
                    FROM telemetry_events
                    WHERE created_at < ?
                    GROUP BY
                        month,
                        repository,
                        issue_number,
                        stage,
                        result,
                        code,
                        command_category
                    """,
                    (cutoff,),
                )
            )
            for row in expired:
                connection.execute(
                    """
                    INSERT INTO telemetry_monthly_aggregates (
                        month,
                        repository,
                        issue_number,
                        stage,
                        result,
                        code,
                        command_category,
                        executions_count,
                        attempts_total,
                        duration_ms_total,
                        input_units_total,
                        output_units_total,
                        total_units_total,
                        estimated_cost_cents_total,
                        aggregated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(month, repository, issue_number, stage, result, code, command_category)
                    DO UPDATE SET
                        executions_count = executions_count + excluded.executions_count,
                        attempts_total = attempts_total + excluded.attempts_total,
                        duration_ms_total = duration_ms_total + excluded.duration_ms_total,
                        input_units_total = input_units_total + excluded.input_units_total,
                        output_units_total = output_units_total + excluded.output_units_total,
                        total_units_total = total_units_total + excluded.total_units_total,
                        estimated_cost_cents_total = estimated_cost_cents_total + excluded.estimated_cost_cents_total,
                        aggregated_at = excluded.aggregated_at
                    """,
                    (
                        row["month"],
                        row["repository"],
                        row["issue_number"],
                        row["stage"],
                        row["result"],
                        row["code"],
                        row["command_category"],
                        row["executions_count"],
                        row["attempts_total"],
                        row["duration_ms_total"],
                        row["input_units_total"],
                        row["output_units_total"],
                        row["total_units_total"],
                        row["estimated_cost_cents_total"],
                        aggregated_at,
                    ),
                )
            connection.execute("DELETE FROM telemetry_events WHERE created_at < ?", (cutoff,))

        return TelemetryWriteResult(
            recorded=True,
            code="TELEMETRY_AGGREGATED",
            message="Private telemetry details aggregated and expired details pruned.",
        )

    def _connect(self) -> sqlite3.Connection:
        assert self.db_path is not None
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS telemetry_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    execution_id TEXT,
                    repository TEXT,
                    issue_number INTEGER,
                    stage TEXT,
                    command_category TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    result TEXT,
                    attempts INTEGER,
                    code TEXT,
                    input_units INTEGER,
                    output_units INTEGER,
                    total_units INTEGER,
                    estimated_cost_cents INTEGER,
                    technical_ref TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS telemetry_monthly_aggregates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month TEXT NOT NULL,
                    repository TEXT,
                    issue_number INTEGER,
                    stage TEXT,
                    result TEXT,
                    code TEXT,
                    command_category TEXT,
                    executions_count INTEGER NOT NULL,
                    attempts_total INTEGER NOT NULL,
                    duration_ms_total INTEGER NOT NULL,
                    input_units_total INTEGER NOT NULL,
                    output_units_total INTEGER NOT NULL,
                    total_units_total INTEGER NOT NULL,
                    estimated_cost_cents_total INTEGER NOT NULL,
                    aggregated_at TEXT NOT NULL,
                    UNIQUE(month, repository, issue_number, stage, result, code, command_category)
                );
                """
            )


def _contains_forbidden_content(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = str(key).lower()
            if normalized_key in FORBIDDEN_EVENT_FIELDS:
                return True
            if _contains_forbidden_content(nested_value):
                return True
    elif isinstance(value, list | tuple | set):
        return any(_contains_forbidden_content(item) for item in value)
    return False


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()
