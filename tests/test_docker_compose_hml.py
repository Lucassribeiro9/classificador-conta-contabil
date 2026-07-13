from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.hml.yml"


def test_hml_compose_isolates_database_and_exposes_services_only_to_edge_network():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"api", "frontend", "postgres"} <= services.keys()
    assert all("ports" not in service for service in services.values())

    postgres = services["postgres"]
    assert postgres["networks"] == ["hml-db"]
    assert postgres["volumes"] == [
        "postgres-hml-data:/var/lib/postgresql/data"
    ]
    assert "healthcheck" in postgres

    api = services["api"]
    assert set(api["networks"]) == {"hml-db", "hml-edge"}
    assert api["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert "healthcheck" in api

    frontend = services["frontend"]
    assert frontend["networks"] == ["hml-edge"]
    assert frontend["depends_on"]["api"]["condition"] == "service_healthy"
    assert frontend["build"]["args"]["VITE_API_BASE_URL"] == "/api"
    assert "healthcheck" in frontend

    assert compose["networks"]["hml-db"]["internal"] is True
    assert compose["networks"]["hml-edge"] == {
        "external": True,
        "name": "classificador-hml-edge",
    }
    assert compose["volumes"]["postgres-hml-data"]["name"] == (
        "classificador-hml-postgres-data"
    )


def test_hml_environment_example_and_validation_commands_are_sanitized():
    env_example = (PROJECT_ROOT / ".env.hml.example").read_text(encoding="utf-8")
    deployment_guide = (PROJECT_ROOT / "docs/devops-hml.md").read_text(
        encoding="utf-8"
    )
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    expected_variables = {
        "APP_ENV=hml",
        "FRONTEND_PUBLIC_URL=https://classificador-hml.interno",
        "API_PUBLIC_URL=https://classificador-hml.interno/api",
        "POSTGRES_DB=classificador_hml",
        "POSTGRES_USER=classificador_hml",
        "DATABASE_URL=postgresql+psycopg://classificador_hml:CHANGE_ME",
        "ADMIN_TOKEN=CHANGE_ME",
        "JWT_SECRET_KEY=CHANGE_ME",
        "CORS_ALLOWED_ORIGINS=https://classificador-hml.interno",
    }
    assert all(variable in env_example for variable in expected_variables)
    assert "!.env.hml.example" in gitignore

    assert "docker network create classificador-hml-edge" in deployment_guide
    assert "docker compose --env-file .env.hml -f docker-compose.hml.yml config" in (
        deployment_guide
    )
    assert "docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --build" in (
        deployment_guide
    )
    assert "https://classificador-hml.interno/api/health" in deployment_guide
    assert "https://classificador-hml.interno/login" in deployment_guide
