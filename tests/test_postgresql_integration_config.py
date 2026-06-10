from configparser import ConfigParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_makefile_exposes_dedicated_postgresql_integration_command():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "test-postgres:" in makefile
    assert "classificador-conta-contabil-test" in makefile
    assert "up -d --build $(SERVICE_API) $(SERVICE_DB)" in makefile
    assert "pytest -q -m integration_postgres tests/integration" in makefile
    assert "down -v" in makefile


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
