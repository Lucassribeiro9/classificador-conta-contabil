"""Safe, local JSON logging for technical diagnostics."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from api.request_context import get_current_request_id


TECHNICAL_LOG_RETENTION_DAYS = 30
_HANDLER_MARKER = "_classificador_technical_logging"
_ALLOWED_EXTRA_FIELDS = {
    "duration_ms",
    "error_type",
    "event",
    "method",
    "request_id",
    "route",
    "service",
    "status_code",
}
_SECRET_PATTERN = re.compile(
    r"(?i)\b(password|senha|token|api[_-]?key|secret|authorization|cookie)\b"
    r"\s*[:=]\s*[^\s,;]+"
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s,;]+")


def _redact_message(message: str) -> str:
    message = _SECRET_PATTERN.sub(r"\1=[REDACTED]", message)
    return _BEARER_PATTERN.sub("Bearer [REDACTED]", message)


def _safe_extra_value(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return None


class _TechnicalLogFilter(logging.Filter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "service", None):
            record.service = self.service
        if not getattr(record, "request_id", None):
            request_id = get_current_request_id()
            if request_id:
                record.request_id = request_id
        return True


class _JsonTechnicalFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact_message(record.getMessage()),
        }
        for field in _ALLOWED_EXTRA_FIELDS:
            value = _safe_extra_value(getattr(record, field, None))
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class _SafeTechnicalFileHandler(TimedRotatingFileHandler):
    """Discard logging failures so diagnostics cannot break business work."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        # Never echo a message or traceback that could contain sensitive data.
        return None


def _remove_technical_handlers(root: logging.Logger) -> None:
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)
            handler.close()


def configure_technical_logging(
    *, service: str, log_dir: str | Path, retention_days: int = TECHNICAL_LOG_RETENTION_DAYS
) -> Path:
    """Configure one isolated JSONL file for a service and return its path."""
    if retention_days != TECHNICAL_LOG_RETENTION_DAYS:
        raise ValueError("A retencao tecnica deve permanecer em 30 dias.")
    if not service or "/" in service or "\\" in service:
        raise ValueError("service invalido")

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{service}.jsonl"
    handler = _SafeTechnicalFileHandler(
        path,
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
        utc=True,
    )
    setattr(handler, _HANDLER_MARKER, True)
    handler.setFormatter(_JsonTechnicalFormatter())
    handler.addFilter(_TechnicalLogFilter(service))

    root = logging.getLogger()
    _remove_technical_handlers(root)
    root.addHandler(handler)
    root.setLevel(min(root.level or logging.INFO, logging.INFO))
    logging.raiseExceptions = False
    return path
