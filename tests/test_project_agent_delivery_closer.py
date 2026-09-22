import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / ".agents/agents/delivery-closer.md"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"


def _load_agent() -> tuple[dict, str]:
    content = AGENT_PATH.read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)
    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)


def test_delivery_closer_frontmatter_matches_project_agent_contract():
    metadata, _ = _load_agent()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(metadata)
    assert metadata["id"] == "delivery-closer"
    assert metadata["blueprint"] == "close-delivery"
    assert metadata["inputs"] == ["pull_request", "project_context"]
    assert metadata["outputs"] == ["closure_result"]
    assert metadata["providers"]["git"]["access"] == "write"
    assert metadata["providers"]["terminal"]["access"] == "write"
    assert metadata["handoff"] == {
        "next": None,
        "gate": "none",
    }


def test_delivery_closer_requires_authoritative_merge_proof():
    _, body = _load_agent()

    for required_text in (
        "GitHub MCP/API",
        "gh",
        "Local Git",
        "merged=true",
        "merge_commit_sha",
        "updated main",
    ):
        assert required_text in body


def test_delivery_closer_preserves_dirty_work_and_cleanup_order():
    _, body = _load_agent()

    for required_text in (
        "fast-forward-only",
        "Never force",
        "reset destructively",
        "clean",
        "auto-stash",
        "dirty worktree",
        "worktree before the local branch",
        "already absent",
        "active PR shares the same head",
    ):
        assert required_text in body


def test_delivery_closer_never_closes_issue_as_compensation():
    _, body = _load_agent()

    assert "Never close the issue manually" in body
    assert "There is no next Agent" in body
