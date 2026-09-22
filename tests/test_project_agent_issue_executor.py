import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / ".agents/agents/issue-executor.md"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"


def _load_agent() -> tuple[dict, str]:
    content = AGENT_PATH.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)
    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)


def test_issue_executor_frontmatter_matches_project_agent_contract():
    metadata, _ = _load_agent()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(metadata)
    assert metadata["id"] == "issue-executor"
    assert metadata["blueprint"] == "execute-issue"
    assert metadata["inputs"] == ["execution_plan", "project_context"]
    assert metadata["outputs"] == ["execution_evidence"]
    assert metadata["providers"]["git"]["access"] == "write"
    assert metadata["providers"]["terminal"]["access"] == "write"
    assert metadata["handoff"] == {
        "next": "pr-reviewer",
        "gate": "none",
    }


def test_issue_executor_requires_approved_plan_and_routes_material_deviation():
    _, body = _load_agent()

    for required_text in (
        "explicitly approved Execution Plan",
        "planning authority",
        "Revalidate",
        "local deviation",
        "material deviation",
        "needs_re_review",
        "Task Reviewer",
        "Required stages are never skipped",
        "TDD",
        "semantic commits",
        "final approved push",
        "Execution Evidence",
    ):
        assert required_text in body


def test_issue_executor_forbids_scope_and_pr_ownership_expansion():
    _, body = _load_agent()

    for required_text in (
        "Never widen scope",
        "force push",
        "merge",
        "Draft PR",
        "material deviation",
    ):
        assert required_text in body


def test_issue_executor_has_only_expected_project_and_provider_permissions():
    metadata, _ = _load_agent()

    assert metadata["project"]["repository"] == (
        "Lucassribeiro9/classificador-conta-contabil"
    )
    assert set(metadata["providers"]) == {"github", "git", "terminal"}
    assert metadata["providers"]["github"]["preferred"] == "mcp"
    assert metadata["providers"]["github"]["fallback"] == ["gh"]
