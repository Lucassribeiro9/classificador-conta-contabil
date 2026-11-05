"""Observability contract at the HTTP and scrape boundaries."""

from prometheus_client import generate_latest

from core.operational_metrics import REGISTRY


def test_http_metrics_aggregate_route_without_request_content(client):
    secret = "cliente-secreto-508"
    response = client.get(f"/health?empresa={secret}", headers={"X-Request-ID": secret})

    assert response.status_code == 200
    sample = generate_latest(REGISTRY).decode("utf-8")
    assert (
        'classificador_http_requests_total{method="GET",route="/health",status="2xx"}'
        in sample
    )
    assert (
        'classificador_http_request_duration_seconds_count{method="GET",route="/health",status="2xx"}'
        in sample
    )
    assert secret not in sample
    assert "empresa=" not in sample


def test_scrape_uses_separate_private_listener_not_api_route(client):
    from urllib.request import urlopen

    from core.operational_metrics import start_private_metrics_server

    assert client.get("/metrics").status_code == 404
    server, thread = start_private_metrics_server("127.0.0.1", 0)
    try:
        assert server.server_address[0] == "127.0.0.1"
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/metrics", timeout=2
        ) as response:
            sample = response.read().decode("utf-8")
        assert "classificador_http_requests_total" in sample
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_lifespan_serves_metrics_on_configured_private_listener(monkeypatch):
    import asyncio
    import socket
    from urllib.request import urlopen

    from api.main import app, lifespan
    from core.config import settings

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    monkeypatch.setattr(settings, "METRICS_NETWORK_PEER", "127.0.0.1")
    monkeypatch.setattr(settings, "METRICS_PORT", port)

    async def exercise():
        async with lifespan(app):
            with urlopen(f"http://127.0.0.1:{port}/metrics", timeout=2) as response:
                assert response.status == 200
                assert b"classificador_http_requests_total" in response.read()

    asyncio.run(exercise())
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0


def test_metrics_failure_does_not_change_business_response(client, monkeypatch):
    import api.main

    def fail(*_args):
        raise RuntimeError("metrics offline")

    monkeypatch.setattr(api.main, "observe_http_request", fail)
    response = client.get("/health")
    assert response.status_code == 200


def test_scrape_includes_bounded_api_process_health():
    sample = generate_latest(REGISTRY).decode("utf-8")
    assert "process_resident_memory_bytes" in sample
    assert "process_cpu_seconds_total" in sample


def test_worker_exporter_reports_process_without_database_or_api_series():
    from urllib.request import urlopen

    from core.operational_metrics import start_private_process_metrics_server

    server, thread = start_private_process_metrics_server("127.0.0.1", 0)
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/metrics", timeout=2) as response:
            sample = response.read().decode("utf-8")
        assert "process_resident_memory_bytes" in sample
        assert "classificador_ml_jobs" not in sample
        assert "classificador_http_requests_total" not in sample
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
