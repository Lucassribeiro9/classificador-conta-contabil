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
    assert set(jobs) == {"backend", "frontend", "docker-compose"}
    assert all(job["runs-on"] == "ubuntu-latest" for job in jobs.values())

    backend = jobs["backend"]
    assert any(step.get("uses") == "actions/setup-python@v6" for step in backend["steps"])
    assert "python -m pip install -r requirements.txt" in _commands(backend)
    assert _commands(backend)[-1] == "python -m pytest -q tests"
    assert all(
        step.get("name") != "Run order-sensitive duplicate-file audit test"
        for step in backend["steps"]
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

    compose_commands = "\n".join(_commands(jobs["docker-compose"]))
    assert "docker compose --env-file .env.example -f docker-compose.yml config --quiet" in compose_commands
    assert "docker compose --env-file .env.hml.example -f docker-compose.hml.yml config --quiet" in compose_commands
    assert "docker compose --env-file .env.prod.example -f docker-compose.prod.yml config --quiet" in compose_commands

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "Known failures:" not in workflow_text
    assert "--ignore" not in workflow_text
    assert "--deselect" not in workflow_text
    assert "secrets." not in workflow_text
