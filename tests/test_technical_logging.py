import json
import logging
from logging.handlers import TimedRotatingFileHandler

from core.technical_logging import configure_technical_logging


def test_technical_log_is_json_and_drops_unapproved_extra_fields(tmp_path):
    configure_technical_logging(service="test", log_dir=tmp_path)

    logging.getLogger("test.contract").info(
        "operacao concluida",
        extra={
            "event": "operation.completed",
            "request_id": "request-123",
            "status_code": 200,
            "empresa_id": 42,
            "payload": {"historico": "nao registrar"},
        },
    )

    for handler in logging.getLogger().handlers:
        handler.flush()

    record = json.loads((tmp_path / "test.jsonl").read_text(encoding="utf-8"))

    assert record == {
        "timestamp": record["timestamp"],
        "level": "INFO",
        "logger": "test.contract",
        "event": "operation.completed",
        "message": "operacao concluida",
        "request_id": "request-123",
        "status_code": 200,
        "service": "test",
    }
    assert "empresa_id" not in record
    assert "payload" not in record


def test_technical_log_redacts_secrets_and_rotates(tmp_path):
    configure_technical_logging(service="rotation", log_dir=tmp_path)
    logger = logging.getLogger("test.redaction")
    logger.info("token=secret-token password:senha-secreta")

    handler = next(
        item
        for item in logging.getLogger().handlers
        if getattr(item, "_classificador_technical_logging", False)
    )
    handler.flush()
    handler.doRollover()

    records = [
        json.loads(line)
        for line in (tmp_path / "rotation.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records == []
    rotated = list(tmp_path.glob("rotation.jsonl.*"))
    assert rotated
    assert "secret-token" not in rotated[0].read_text(encoding="utf-8")
    assert "senha-secreta" not in rotated[0].read_text(encoding="utf-8")


def test_technical_log_destination_failure_does_not_escape(monkeypatch, tmp_path):
    configure_technical_logging(service="failure", log_dir=tmp_path)
    monkeypatch.setattr(
        TimedRotatingFileHandler,
        "emit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("destination down")),
    )

    logging.getLogger("test.failure").error("business operation completed")
