import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / ".agents/agents/pr-reviewer.md"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"


def _load_agent() -> tuple[dict, str]:
    content = AGENT_PATH.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)
    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)


def test_pr_reviewer_frontmatter_matches_project_agent_contract():
    metadata, _ = _load_agent()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(metadata)
    assert metadata["id"] == "pr-reviewer"
    assert metadata["blueprint"] == "draft-pr"
    assert metadata["inputs"] == [
        "execution_plan",
        "execution_evidence",
        "project_context",
    ]
    assert metadata["outputs"] == ["findings", "draft_pr"]
    assert metadata["providers"]["git"]["access"] == "read"
    assert metadata["providers"]["terminal"]["access"] == "read"
    assert metadata["handoff"] == {
        "next": "human_review",
        "gate": "human_review_merge",
    }


def test_pr_reviewer_prioritizes_observed_branch_state_over_evidence():
    _, body = _load_agent()

    assert "HEAD, diff, commits" in body
    assert "observed truth" in body
    assert "never overrides contradictory branch state" in body


def test_pr_reviewer_routes_findings_without_implementing():
    _, body = _load_agent()

    for required_text in (
        "informational",
        "warning",
        "blocking",
        "local",
        "material",
        "Issue Executor",
        "Task Reviewer",
        "Draft PR",
        "Never edit implementation files",
        "mark a PR ready",
        "merge",
    ):
        assert required_text in body


def test_pr_reviewer_keeps_pr_lifecycle_guards():
    _, body = _load_agent()

    for required_text in (
        "idempotently by head branch",
        "Never create a duplicate",
        "demote a ready PR",
        "merged/closed PR",
        "Pending CI",
        "failed CI",
    ):
        assert required_text in body
