import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / ".agents/agents/task-reviewer.md"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"


def _load_agent(path: Path) -> tuple[dict, str]:
    content = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)
    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)


def test_task_reviewer_frontmatter_matches_project_agent_contract():
    metadata, _ = _load_agent(AGENT_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(metadata)
    assert metadata["id"] == "task-reviewer"
    assert metadata["project"] == {
        "id": "classificador-conta-contabil",
        "repository": "Lucassribeiro9/classificador-conta-contabil",
    }
    assert metadata["blueprint"] == "task-review"
    assert metadata["outputs"] == ["review_report", "execution_plan"]
    assert metadata["handoff"] == {
        "next": "issue-executor",
        "gate": "human_approval",
    }


def test_task_reviewer_body_keeps_context_rules_and_stays_thin():
    _, body = _load_agent(AGENT_PATH)

    for required_text in (
        "Project Context Envelope",
        "task-review",
        "observed stack",
        "expected path",
        "material ambiguity",
        "schema version 1.1",
        "capabilities",
        "structured references",
        "Never implement",
        "invoke the Issue Executor automatically",
    ):
        assert required_text in body

    for forbidden_text in (
        "git checkout -b",
        "git worktree add",
        "pytest",
        "RED",
        "GREEN",
        "git commit",
        "create pull request",
    ):
        assert forbidden_text not in body


def test_task_reviewer_is_bound_to_classificador_repository():
    metadata, _ = _load_agent(AGENT_PATH)

    assert (
        metadata["project"]["repository"]
        == "Lucassribeiro9/classificador-conta-contabil"
    )
    assert metadata["context"]["bootstrap"] == (
        "../references/project-context-bootstrap.md"
    )
