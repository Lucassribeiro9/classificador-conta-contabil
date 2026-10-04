import asyncio
import json
import logging

from api.main import app, lifespan
from core.technical_logging import configure_technical_logging


def test_http_request_is_logged_with_safe_request_id(client, tmp_path):
    configure_technical_logging(service="api", log_dir=tmp_path)

    response = client.get("/health", headers={"X-Request-ID": "api-test-123"})

    assert response.status_code == 200
    for handler in logging.getLogger().handlers:
        handler.flush()

    records = [
        json.loads(line)
        for line in (tmp_path / "api.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    record = next(item for item in records if item.get("event") == "http.request")
    assert record["event"] == "http.request"
    assert record["request_id"] == "api-test-123"
    assert record["method"] == "GET"
    assert record["status_code"] == 200
    assert record["route"] == "/health"
    assert "headers" not in record
    assert "body" not in record
    assert "detail" not in record


def test_api_lifespan_configures_its_log_destination(monkeypatch, tmp_path):
    import api.main

    monkeypatch.setattr(api.main.settings, "TECHNICAL_LOG_DIR", str(tmp_path))

    async def exercise_lifespan():
        async with lifespan(app):
            logging.getLogger("api-lifespan-test").info("lifespan configured")

    asyncio.run(exercise_lifespan())

    for handler in logging.getLogger().handlers:
        handler.flush()
    assert (tmp_path / "api.jsonl").exists()
