from pathlib import Path
from string import Template

from dotenv import dotenv_values
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_compose() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())


def _environment_as_dict(raw_environment) -> dict[str, str]:
    if isinstance(raw_environment, dict):
        return raw_environment

    environment = {}
    for item in raw_environment:
        key, _, value = item.partition("=")
        environment[key] = value

    return environment


def _resolve_env_value(value: str) -> str:
    env_values = {key: value for key, value in dotenv_values(PROJECT_ROOT / ".env").items()}

    previous = None
    resolved = value
    while resolved != previous:
        previous = resolved
        resolved = Template(resolved).safe_substitute(env_values)

    return resolved


def test_docker_compose_runs_api_with_private_postgresql_service():
    compose = _load_compose()

    services = compose["services"]
    api_service = services["api-contabil"]
    postgres_service = services["postgres"]

    api_environment = _environment_as_dict(api_service["environment"])
    database_url = _resolve_env_value(api_environment["DATABASE_URL"])

    assert database_url.startswith("postgresql+psycopg://")
    assert "@postgres:5432/" in database_url
    assert "ports" not in postgres_service
    assert postgres_service["volumes"] == ["postgres-data:/var/lib/postgresql/data"]
    assert "postgres-data" in compose["volumes"]
    assert "postgres" in api_service["depends_on"]


def test_dev_compose_runs_razao_worker_with_shared_private_storage():
    compose = _load_compose()
    services = compose["services"]
    api = services["api-contabil"]
    worker = services["razao-worker"]

    assert worker["build"] == api["build"]
    assert worker["image"] == api["image"]
    assert "ports" not in worker
    assert worker["depends_on"] == api["depends_on"]
    assert worker["networks"] == api["networks"]
    assert worker["volumes"] == [
        "razao-temp-dev:/app/data/razao-temporario",
        "technical-logs-worker-dev:/app/data/logs",
    ]
    assert "razao-temp-dev:/app/data/razao-temporario" in api["volumes"]
    assert worker["command"] == "python -m scripts.razao_worker"
    assert compose["volumes"]["razao-temp-dev"]["name"] == (
        "${RAZAO_TEMP_VOLUME_NAME:-classificador-dev-razao-temp}"
    )


def test_make_cleanup_is_project_scoped_and_preserves_persistent_data_by_default():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker system prune" not in makefile
    assert "docker builder prune" not in makefile
    assert "clean-project:\n\t$(DOCKER_COMPOSE) down --rmi local" in makefile
    assert "clean-razao-temp:\n\t$(DOCKER_COMPOSE) down" in makefile
    assert "export RAZAO_TEMP_VOLUME_NAME ?= classificador-dev-razao-temp" in makefile
    assert "\tdocker volume rm $(RAZAO_TEMP_VOLUME_NAME)" in makefile


def test_postgres_harness_uses_isolated_temp_volume_without_publishing_api_port():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "RAZAO_TEMP_VOLUME_NAME=classificador-conta-contabil-test-razao-temp" in makefile
    assert "up -d --build $(SERVICE_DB)" in makefile
    assert "up -d --build $(SERVICE_API) $(SERVICE_DB)" not in makefile
    assert "run --build --rm $(SERVICE_API)" in makefile


def test_dev_razao_limits_are_configurable_for_api_and_worker():
    compose = _load_compose()
    api_environment = _environment_as_dict(compose["services"]["api-contabil"]["environment"])
    worker_environment = _environment_as_dict(compose["services"]["razao-worker"]["environment"])
    expected = {
        "TECHNICAL_LOG_DIR": "${TECHNICAL_LOG_DIR:-/app/data/logs}",
        "RAZAO_STORAGE_DIR": "/app/data/razao-temporario",
        "RAZAO_UPLOAD_MAX_BYTES": "${RAZAO_UPLOAD_MAX_BYTES:-50000000}",
        "RAZAO_STORAGE_MIN_FREE_BYTES": "${RAZAO_STORAGE_MIN_FREE_BYTES:-5000000000}",
        "RAZAO_STORAGE_MIN_FREE_RATIO": "${RAZAO_STORAGE_MIN_FREE_RATIO:-0.15}",
        "RAZAO_FAILED_RETENTION_SECONDS": "${RAZAO_FAILED_RETENTION_SECONDS:-86400}",
        "RAZAO_IMPORT_BLOCK_SIZE": "${RAZAO_IMPORT_BLOCK_SIZE:-1000}",
        "RAZAO_WORKER_CONCURRENCY": "${RAZAO_WORKER_CONCURRENCY:-1}",
        "RAZAO_HEARTBEAT_SECONDS": "${RAZAO_HEARTBEAT_SECONDS:-30}",
        "RAZAO_LEASE_SECONDS": "${RAZAO_LEASE_SECONDS:-600}",
        "RAZAO_POLL_INTERVAL_SECONDS": "${RAZAO_POLL_INTERVAL_SECONDS:-3}",
    }

    assert expected.items() <= api_environment.items()
    assert expected.items() <= worker_environment.items()

    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    for key, value in {
        "TECHNICAL_LOG_DIR": "./data/logs",
        "RAZAO_UPLOAD_MAX_BYTES": "50000000",
        "RAZAO_STORAGE_MIN_FREE_BYTES": "5000000000",
        "RAZAO_STORAGE_MIN_FREE_RATIO": "0.15",
        "RAZAO_FAILED_RETENTION_SECONDS": "86400",
        "RAZAO_IMPORT_BLOCK_SIZE": "1000",
        "RAZAO_WORKER_CONCURRENCY": "1",
        "RAZAO_HEARTBEAT_SECONDS": "30",
        "RAZAO_LEASE_SECONDS": "600",
        "RAZAO_POLL_INTERVAL_SECONDS": "3",
    }.items():
        assert f"{key}={value}" in env_example
