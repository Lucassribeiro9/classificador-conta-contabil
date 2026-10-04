from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github/workflows/ci.yml"


def _commands(job: dict) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def test_ci_validates_backend_frontend_and_compose_without_secrets():
    workflow = yaml.load(
        WORKFLOW_PATH.read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )

    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert "pull_request" in workflow["on"]

    jobs = workflow["jobs"]
    assert set(jobs) == {
        "backend",
        "postgres",
        "frontend",
        "playwright",
        "docker-compose",
        "docs",
        "security",
    }
    assert all(job["runs-on"] == "ubuntu-latest" for job in jobs.values())
    assert all(
        any(
            step.get("uses") == "actions/checkout@v6"
            and step.get("with", {}).get("fetch-depth") == "0"
            for step in job["steps"]
        )
        for job in jobs.values()
    )

    backend = jobs["backend"]
    assert any(step.get("uses") == "actions/setup-python@v6" for step in backend["steps"])
    assert "python -m pip install -r requirements.txt" in _commands(backend)
    assert _commands(backend)[-2:] == [
        "python -m ruff check .",
        "python -m pytest -q tests",
    ]
    assert all(
        step.get("name") != "Run order-sensitive duplicate-file audit test"
        for step in backend["steps"]
    )

    postgres = jobs["postgres"]
    assert postgres["services"]["postgres"]["image"] == "postgres:16-alpine"
    assert postgres["services"]["postgres"]["ports"] == ["5432:5432"]
    postgres_commands = _commands(postgres)
    assert "python -m alembic upgrade head" in postgres_commands
    assert any(
        "pytest -q -m integration_postgres tests/integration" in command
        for command in postgres_commands
    )
    assert postgres["env"]["DATABASE_URL"].startswith(
        "postgresql+psycopg://"
    )

    frontend = jobs["frontend"]
    assert any(step.get("uses") == "actions/setup-node@v6" for step in frontend["steps"])
    assert _commands(frontend)[-5:] == [
        "npm ci",
        "npm run lint",
        "npm run typecheck",
        "npm test",
        "npm run build",
    ]

    playwright = jobs["playwright"]
    assert playwright["defaults"]["run"]["working-directory"] == "frontend"
    assert "npx playwright install --with-deps chromium" in _commands(playwright)
    assert "npm run test:e2e" in _commands(playwright)

    compose_commands = "\n".join(_commands(jobs["docker-compose"]))
    assert "docker compose --env-file .env.example -f docker-compose.yml config --quiet" in compose_commands
    assert "docker compose --env-file .env.hml.example -f docker-compose.hml.yml config --quiet" in compose_commands
    assert "docker compose --env-file .env.hml.example -f docker-compose.edge.yml config --quiet" in compose_commands
    assert "docker compose --env-file .env.prod.example -f docker-compose.prod.yml config --quiet" in compose_commands

    docs = jobs["docs"]
    assert "python -m pip install -r requirements.txt" in _commands(docs)
    assert "python -m pytest -q tests/test_*docs.py" in _commands(docs)

    security = jobs["security"]
    assert "python scripts/check_diff_security.py --base-ref origin/main" in _commands(
        security
    )

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Known failures:" not in workflow_text
    assert "--ignore" not in workflow_text
    assert "--deselect" not in workflow_text
    assert "continue-on-error" not in workflow_text
    assert "secrets." not in workflow_text
