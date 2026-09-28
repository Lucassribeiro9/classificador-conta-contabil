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


def test_environment_test_targets_delegate_once_to_the_canonical_local_suite():
    result = run_make("-n", "dev-test", "hml-test", "prod-test", "all-test")
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("./venv/bin/python -m pytest -q tests") == 1
    assert "docker compose --env-file .env -f docker-compose.yml run" not in result.stdout
    assert "docker compose --env-file .env.hml -f docker-compose.hml.yml run" not in result.stdout
    for target in ("dev-test", "hml-test", "prod-test", "all-test"):
        assert f"{target}: test" in makefile


def test_up_and_down_targets_preserve_volumes_and_order_hml_before_edge():
    result = run_make("-n", "dev-up", "dev-down", "hml-up", "edge-up", "edge-down", "hml-down")

    assert result.returncode == 0, result.stderr
    assert "docker compose --env-file .env -f docker-compose.yml up -d --wait" in result.stdout
    assert "docker compose --env-file .env -f docker-compose.yml down" in result.stdout
    assert "docker network inspect classificador-hml-edge" in result.stdout
    hml_up = "docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --wait"
    edge_up = "docker compose --env-file .env.hml -f docker-compose.edge.yml up -d --wait"
    edge_down = "docker compose --env-file .env.hml -f docker-compose.edge.yml down"
    hml_down = "docker compose --env-file .env.hml -f docker-compose.hml.yml down"
    assert result.stdout.index(hml_up) < result.stdout.index(edge_up)
    assert result.stdout.index(edge_down) < result.stdout.index(hml_down)
    assert "down -v" not in result.stdout
    assert "--volumes" not in result.stdout


def test_production_up_and_down_require_exact_confirmation_and_preflight():
    denied_up = run_make("DOCKER_COMPOSE=true", "DOCKER=true", "prod-up")
    denied_down = run_make("DOCKER_COMPOSE=true", "DOCKER=true", "prod-down")
    confirmed_up = run_make(
        "DOCKER_COMPOSE=true", "DOCKER=true", "prod-up", CONFIRM_PROD="prod-up"
    )
    confirmed_down = run_make(
        "DOCKER_COMPOSE=true", "DOCKER=true", "prod-down", CONFIRM_PROD="prod-down"
    )
    dry_run = run_make("-n", "prod-up", "prod-down")

    assert denied_up.returncode == 2
    assert denied_down.returncode == 2
    assert "CONFIRM_PROD=prod-up" in denied_up.stderr
    assert "CONFIRM_PROD=prod-down" in denied_down.stderr
    assert confirmed_up.returncode == 0, confirmed_up.stderr
    assert confirmed_down.returncode == 0, confirmed_down.stderr
    assert "docker compose --env-file .env.prod -f docker-compose.prod.yml config --quiet" in dry_run.stdout
    assert "docker network inspect classificador-prod-edge" in dry_run.stdout
    assert "docker network create classificador-prod-edge" in dry_run.stdout
    assert "down -v" not in dry_run.stdout
    assert "--volumes" not in dry_run.stdout

    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    prod_down = makefile.split("prod-down:", maxsplit=1)[1].split(
        "# Credenciais", maxsplit=1
    )[0]
    assert "network inspect" not in prod_down
    assert "network create" not in prod_down


def test_up_targets_validate_compose_without_printing_resolved_environment():
    result = run_make("-n", "hml-up", "edge-up", "prod-up")

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("config --quiet") == 3
    assert " config\n" not in result.stdout


def test_registry_login_requires_external_credentials_without_echoing_token():
    missing = run_make("DOCKER=true", "registry-login")
    configured = run_make(
        "DOCKER=true",
        "registry-login",
        REGISTRY_HOST="registry.invalid",
        REGISTRY_USERNAME="operator",
        REGISTRY_TOKEN="sanitized-token",
    )

    assert missing.returncode == 2
    assert "REGISTRY_HOST, REGISTRY_USERNAME e REGISTRY_TOKEN" in missing.stderr
    assert configured.returncode == 0, configured.stderr
    assert "sanitized-token" not in configured.stdout
    assert "sanitized-token" not in configured.stderr



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
    assert "docker-compose.prod.yml up -d --wait" not in result.stdout
    assert "docker-compose.prod.yml down" not in result.stdout
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
        "dev-up", "dev-down", "hml-up", "hml-down", "edge-up", "edge-down",
        "registry-login",
    ):
        assert f"make {target}" in readme
    assert "CONFIRM_PROD=prod-build" in readme
    assert "CONFIRM_PROD=prod-clean-cache" in readme
    assert "CONFIRM_PROD=prod-up" in readme
    assert "CONFIRM_PROD=prod-down" in readme
