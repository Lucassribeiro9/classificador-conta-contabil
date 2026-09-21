import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / ".agents/agents"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"
FIXTURES = ROOT / "tests/fixtures/project_agents"

EXPECTED = {
    "task-reviewer": {
        "blueprint": "task-review",
        "next": "issue-executor",
        "gate": "human_approval",
    },
    "issue-executor": {
        "blueprint": "execute-issue",
        "next": "pr-reviewer",
        "gate": "none",
    },
    "pr-reviewer": {
        "blueprint": "draft-pr",
        "next": "human_review",
        "gate": "human_review_merge",
    },
    "delivery-closer": {
        "blueprint": "close-delivery",
        "next": None,
        "gate": "none",
    },
}


def _load_agent(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)
    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_all_project_agents_validate_and_share_project_binding():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    seen = set()

    for path in sorted(AGENTS_PATH.glob("*.md")):
        metadata, _ = _load_agent(path)
        validator.validate(metadata)
        seen.add(metadata["id"])

        assert metadata["project"] == {
            "id": "classificador-conta-contabil",
            "repository": "Lucassribeiro9/classificador-conta-contabil",
        }
        assert metadata["context"]["bootstrap"] == (
            "../references/project-context-bootstrap.md"
        )
        assert metadata["blueprint"] == EXPECTED[metadata["id"]]["blueprint"]
        assert metadata["handoff"]["next"] == EXPECTED[metadata["id"]]["next"]
        assert metadata["handoff"]["gate"] == EXPECTED[metadata["id"]]["gate"]

    assert seen == set(EXPECTED)


def test_happy_path_preserves_both_human_gates():
    flow = _load_json("happy-path-handoffs.json")
    steps = flow["steps"]

    assert steps[0]["gate"] == "human_approval"
    assert steps[2]["gate"] == "human_review_merge"
    assert steps[-1]["status"] == "completed"
    assert steps[-1]["next_agent"] is None


def test_material_deviation_returns_to_task_reviewer_for_new_revision():
    flow = _load_json("material-deviation-handoffs.json")
    steps = flow["steps"]

    assert steps[1] == {
        "current_agent": "issue-executor",
        "status": "needs_re_review",
        "reason": "material_deviation",
        "next_agent": "task-reviewer",
    }
    assert steps[0]["revision"] == 1
    assert steps[2]["revision"] == 2


def test_agent_catalog_lists_project_agents_as_future_isolated_layer():
    catalog = (ROOT / ".agents/README.md").read_text(encoding="utf-8")

    for required_text in (
        "Project Agents",
        "task-reviewer",
        "issue-executor",
        "pr-reviewer",
        "delivery-closer",
        ".agents/contracts/project-agent.schema.json",
        ".agents/contracts/project-context-envelope.schema.json",
        ".agents/references/project-context-bootstrap.md",
        "não fazem parte da operação atual",
        "issue-delivery-loop",
        "integração futura",
    ):
        assert required_text in catalog
