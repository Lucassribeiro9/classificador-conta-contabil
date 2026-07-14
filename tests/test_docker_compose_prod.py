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
        "CORS_ALLOWED_ORIGINS=https://classificador.interno",
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
    assert "docker network create classificador-prod-edge" in runbook
    assert "docker compose --env-file .env.prod -f docker-compose.prod.yml config" in (
        runbook
    )
    assert "docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build" in (
        runbook
    )
    assert "https://classificador.interno/api/health" in runbook
    assert "https://classificador.interno/login" in runbook
