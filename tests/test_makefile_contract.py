"""Testes públicos do contrato para os alvos do Make específicos por ambiente."""

from pathlib import Path
import os
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_make(*args: str, **environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        env={**os.environ, **environment},
        check=False,
    )


def test_dev_build_uses_the_dev_env_file_and_compose_stack():
    result = run_make("-n", "dev-build")

    assert result.returncode == 0, result.stderr
    assert "docker compose --env-file .env -f docker-compose.yml build" in result.stdout


def test_environment_matrix_selects_the_approved_compose_stacks_and_log_tail():
    result = run_make("-n", "dev-test", "dev-clean-cache", "dev-logs", "hml-build", "hml-test", "hml-clean-cache", "hml-logs", "prod-test", "prod-logs")

    assert result.returncode == 0, result.stderr
    assert "docker compose --env-file .env -f docker-compose.yml" in result.stdout
    assert "docker compose --env-file .env.hml -f docker-compose.hml.yml" in result.stdout
    assert "docker compose --env-file .env.hml -f docker-compose.edge.yml" in result.stdout
    assert "docker compose --env-file .env.prod -f docker-compose.prod.yml" in result.stdout
    assert "logs -f --tail 200" in result.stdout
    assert "down --rmi local" in result.stdout



def test_production_mutations_require_exact_confirmation_before_docker():
    denied_build = run_make("DOCKER_COMPOSE=true", "prod-build")
    denied_clean = run_make("DOCKER_COMPOSE=true", "prod-clean-cache")
    confirmed_build = run_make(
        "DOCKER_COMPOSE=true", "prod-build", CONFIRM_PROD="prod-build"
    )
    confirmed_clean = run_make(
        "DOCKER_COMPOSE=true", "prod-clean-cache", CONFIRM_PROD="prod-clean-cache"
    )

    assert denied_build.returncode == 2
    assert denied_clean.returncode == 2
    assert "CONFIRM_PROD=prod-build" in denied_build.stderr
    assert "CONFIRM_PROD=prod-clean-cache" in denied_clean.stderr
    assert confirmed_build.returncode == 0, confirmed_build.stderr
    assert confirmed_clean.returncode == 0, confirmed_clean.stderr


def test_all_aggregators_exclude_prod_mutations_and_include_safe_operations():
    result = run_make("-n", "all-build", "all-test", "all-clean-cache", "all-logs")

    assert result.returncode == 0, result.stderr
    assert "docker-compose.prod.yml build" not in result.stdout
    assert "docker-compose.prod.yml down --rmi local" not in result.stdout
    assert "docker-compose.prod.yml logs -f --tail 200" in result.stdout
    assert "docker-compose.hml.yml build" in result.stdout
    assert "docker-compose.yml build" in result.stdout


def test_legacy_targets_remain_available_and_readme_documents_the_matrix():
    legacy = run_make("-n", "build-all", "logs", "clean-project", "clean-razao-temp")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert legacy.returncode == 0, legacy.stderr
    assert "docker compose build api-contabil n8n-test ngrok" in legacy.stdout
    assert "docker compose logs -f api-contabil" in legacy.stdout
    assert "docker compose down --rmi local" in legacy.stdout
    assert "docker volume rm classificador-dev-razao-temp" in legacy.stdout
    for target in (
        "dev-build", "dev-test", "dev-clean-cache", "dev-logs",
        "hml-build", "hml-test", "hml-clean-cache", "hml-logs",
        "prod-build", "prod-test", "prod-clean-cache", "prod-logs",
        "all-build", "all-test", "all-clean-cache", "all-logs",
    ):
        assert f"make {target}" in readme
    assert "CONFIRM_PROD=prod-build" in readme
    assert "CONFIRM_PROD=prod-clean-cache" in readme
