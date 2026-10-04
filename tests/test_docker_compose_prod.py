from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.prod.yml"


def test_prod_compose_is_private_and_has_no_hml_resource_references():
    compose_text = COMPOSE_PATH.read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    services = compose["services"]

    assert compose["name"] == "classificador-prod"
    assert "hml" not in compose_text.lower()
    assert {"api", "frontend", "postgres"} <= services.keys()
    assert all("ports" not in service for service in services.values())

    postgres = services["postgres"]
    assert postgres["networks"] == ["prod-db"]
    assert postgres["volumes"] == [
        "postgres-prod-data:/var/lib/postgresql/data"
    ]
    assert "healthcheck" in postgres

    api = services["api"]
    assert api["environment"]["APP_ENV"] == "prod"
    assert set(api["networks"]) == {"prod-db", "prod-edge"}
    assert api["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert "healthcheck" in api

    frontend = services["frontend"]
    assert frontend["networks"] == ["prod-edge"]
    assert frontend["depends_on"]["api"]["condition"] == "service_healthy"
    assert frontend["build"]["args"]["VITE_API_BASE_URL"] == "/api"
    assert "healthcheck" in frontend

    assert compose["networks"]["prod-db"]["internal"] is True
    assert compose["networks"]["prod-edge"] == {
        "external": True,
        "name": "classificador-prod-edge",
    }
    assert compose["volumes"]["postgres-prod-data"]["name"] == (
        "classificador-prod-postgres-data"
    )


def test_prod_compose_runs_private_razao_worker_with_environment_storage():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    api = compose["services"]["api"]
    worker = compose["services"]["razao-worker"]

    assert worker["build"] == api["build"]
    assert worker["image"] == api["image"]
    assert worker["networks"] == ["prod-db"]
    assert "ports" not in worker
    assert api["volumes"] == [
        "razao-temp-prod:/app/data/razao-temporario",
        "technical-logs-api-prod:/app/data/logs",
    ]
    assert worker["volumes"] == [
        "razao-temp-prod:/app/data/razao-temporario",
        "technical-logs-worker-prod:/app/data/logs",
    ]
    assert worker["command"] == "python -m scripts.razao_worker"
    assert compose["volumes"]["razao-temp-prod"]["name"] == (
        "classificador-prod-razao-temp"
    )


def test_prod_example_and_runbook_require_release_gate_without_real_secrets():
    env_example = (PROJECT_ROOT / ".env.prod.example").read_text(encoding="utf-8")
    runbook = (PROJECT_ROOT / "docs/devops-prod.md").read_text(encoding="utf-8")
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    expected_variables = {
        "APP_ENV=prod",
        "FRONTEND_PUBLIC_URL=https://classificador.interno",
        "API_PUBLIC_URL=https://classificador.interno/api",
        "POSTGRES_DB_PROD=classificador_prod",
        "POSTGRES_USER_PROD=classificador_prod",
        "DATABASE_URL_PROD=postgresql+psycopg://classificador_prod:CHANGE_ME",
        "ADMIN_TOKEN_PROD=CHANGE_ME",
        "JWT_SECRET_KEY_PROD=CHANGE_ME",
        "SERVICE_CREDENTIAL_SECRET_PROD=CHANGE_ME",
        "TECHNICAL_LOG_DIR_PROD=./data/logs",
        "CORS_ALLOWED_ORIGINS=https://classificador.interno",
        "RAZAO_UPLOAD_MAX_BYTES_PROD=50000000",
        "RAZAO_STORAGE_MIN_FREE_BYTES_PROD=5000000000",
        "RAZAO_STORAGE_MIN_FREE_RATIO_PROD=0.15",
        "RAZAO_FAILED_RETENTION_SECONDS_PROD=86400",
        "RAZAO_IMPORT_BLOCK_SIZE_PROD=1000",
        "RAZAO_WORKER_CONCURRENCY_PROD=1",
        "RAZAO_HEARTBEAT_SECONDS_PROD=30",
        "RAZAO_LEASE_SECONDS_PROD=600",
        "RAZAO_POLL_INTERVAL_SECONDS_PROD=3",
    }
    assert all(variable in env_example for variable in expected_variables)
    assert "hml" not in env_example.lower()
    assert "!.env.prod.example" in gitignore

    required_release_checks = {
        "Homologacao aprovada",
        "testes backend",
        "typecheck, lint e build",
        "backup",
        "rollback",
    }
    assert all(check in runbook for check in required_release_checks)
    assert "make prod-up" in runbook
    assert "docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet" in (
        runbook
    )
    assert "make CONFIRM_PROD=prod-up prod-up" in runbook
    assert "https://classificador.interno/api/health" in runbook
    assert "https://classificador.interno/login" in runbook
