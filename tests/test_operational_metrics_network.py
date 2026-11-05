"""Metrics exposure stays on the private Compose database network."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_hml_and_prod_bind_scrape_to_internal_network_only():
    for profile, network in (("hml", "hml-db"), ("prod", "prod-db")):
        compose = yaml.safe_load((ROOT / f"docker-compose.{profile}.yml").read_text())
        assert compose["networks"][network]["internal"] is True
        for service_name in ("api", "ml-worker", "razao-worker"):
            service = compose["services"][service_name]
            assert network in service["networks"]
            assert "ports" not in service
            assert service["environment"]["METRICS_NETWORK_PEER"] == "postgres"
            assert service["environment"]["METRICS_PORT"] == "9000"

    proxy = (ROOT / "infra/nginx/hml.conf").read_text()
    assert "api:9000" not in proxy
    assert "location /metrics" not in proxy
    assert "location /api/metrics" not in proxy
