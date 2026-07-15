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


def test_hml_compose_uses_only_environment_scoped_runtime_variables():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))

    assert compose["name"] == "classificador-hml"
    assert compose["services"]["api"]["environment"] == {
        "APP_ENV": "hml",
        "DATABASE_URL": (
            "${DATABASE_URL_HML:?Defina DATABASE_URL_HML no ambiente de homologacao}"
        ),
        "ADMIN_TOKEN": (
            "${ADMIN_TOKEN_HML:?Defina ADMIN_TOKEN_HML no ambiente de homologacao}"
        ),
        "JWT_SECRET_KEY": (
            "${JWT_SECRET_KEY_HML:?Defina JWT_SECRET_KEY_HML no ambiente de homologacao}"
        ),
        "JWT_ALGORITHM": "${JWT_ALGORITHM_HML:-HS256}",
        "CORS_ALLOWED_ORIGINS": (
            "${CORS_ALLOWED_ORIGINS_HML:-https://classificador-hml.interno}"
        ),
    }


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
        "POSTGRES_DB_HML=classificador_hml",
        "POSTGRES_USER_HML=classificador_hml",
        "DATABASE_URL_HML=postgresql+psycopg://classificador_hml:CHANGE_ME",
        "ADMIN_TOKEN_HML=CHANGE_ME",
        "JWT_SECRET_KEY_HML=CHANGE_ME",
        "CORS_ALLOWED_ORIGINS_HML=https://classificador-hml.interno",
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


def test_hml_guide_gates_seed_after_healthy_isolated_services():
    deployment_guide = " ".join(
        (PROJECT_ROOT / "docs/devops-hml.md")
        .read_text(encoding="utf-8")
        .split()
    )

    required_content = (
        "docs/homologacao-checklist-tecnico.md",
        "somente depois que `postgres`, `api` e `frontend` estiverem `healthy`",
        "export HML_ADMIN_PASSWORD='<senha-temporaria>'",
        "export HML_OPERATOR_PASSWORD='<senha-temporaria>'",
        "export HML_COMPANY_API_KEY='<chave-temporaria>'",
        "api python -m scripts.seed_homologacao",
        "unset HML_ADMIN_PASSWORD HML_OPERATOR_PASSWORD HML_COMPANY_API_KEY",
    )

    for content in required_content:
        assert content in deployment_guide
