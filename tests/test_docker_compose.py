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
