from configparser import ConfigParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_makefile_exposes_dedicated_postgresql_integration_command():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert (
        "DOCKER_COMPOSE_TEST := RAZAO_TEMP_VOLUME_NAME=classificador-conta-contabil-test-razao-temp "
        "docker compose -p classificador-conta-contabil-test"
    ) in makefile

    target = re.search(r"(?m)^test-postgres:\n((?:\t[^\n]*\n)+)", makefile)
    assert target is not None
    assert target.group(1).splitlines() == [
        "\t$(DOCKER_COMPOSE_TEST) up -d --build $(SERVICE_DB)",
        "\t$(DOCKER_COMPOSE_TEST) run --build --rm $(SERVICE_API) sh -c "
        '"python -m alembic upgrade head && python -m pytest -q -m integration_postgres tests/integration"',
        "\t$(DOCKER_COMPOSE_TEST) down -v",
    ]


def test_default_pytest_run_excludes_postgresql_integration_tests():
    parser = ConfigParser()
    parser.read(ROOT / "pytest.ini", encoding="utf-8")

    pytest_options = parser["pytest"]

    assert "integration_postgres" in pytest_options["markers"]
    assert pytest_options["addopts"] == "-m 'not integration_postgres'"


def test_docker_build_context_includes_only_integration_tests():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "tests/" in dockerignore
    assert "!tests/integration/" in dockerignore
    assert "!tests/integration/**" in dockerignore
