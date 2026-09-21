import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / ".agents/contracts"
FIXTURES = ROOT / "tests/fixtures/project_agents"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_project_agent_schema_accepts_canonical_frontmatter():
    schema = _load_json(CONTRACTS / "project-agent.schema.json")
    payload = _load_yaml(FIXTURES / "agent-frontmatter-valid.yaml")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_project_agent_schema_rejects_unknown_top_level_fields():
    schema = _load_json(CONTRACTS / "project-agent.schema.json")
    payload = _load_yaml(FIXTURES / "agent-frontmatter-invalid-extra-field.yaml")

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)


def test_project_context_envelope_accepts_main_and_worktree():
    schema = _load_json(CONTRACTS / "project-context-envelope.schema.json")
    validator = Draft202012Validator(schema)

    validator.validate(_load_json(FIXTURES / "context-main-valid.json"))
    validator.validate(_load_json(FIXTURES / "context-worktree-valid.json"))


def test_project_context_envelope_rejects_unverified_repository():
    schema = _load_json(CONTRACTS / "project-context-envelope.schema.json")
    payload = _load_json(FIXTURES / "context-invalid-unverified.json")

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)


def test_bootstrap_reference_defines_required_discovery_order_and_blocks():
    content = (
        ROOT / ".agents/references/project-context-bootstrap.md"
    ).read_text(encoding="utf-8")

    for required_text in (
        "explicit override",
        "git rev-parse --show-toplevel",
        "worktree",
        "git remote",
        "project_identity_unverified",
        ".agents/local/project-manifest.yaml",
        ".agents/local/capability-registry.yaml",
        "issue_required",
        "GitHub",
        "Project Context Envelope",
        "in memory",
        "never persist",
    ):
        assert required_text in content


def test_local_agent_configuration_is_ignored_but_agent_definitions_are_not():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".agents/local/" in gitignore
    assert ".agents/agents/" not in gitignore


def test_context_allows_discovery_mode_without_local_files():
    schema = _load_json(CONTRACTS / "project-context-envelope.schema.json")
    payload = _load_json(FIXTURES / "context-discovery-mode-valid.json")

    Draft202012Validator(schema).validate(payload)
    assert payload["project_context"]["manifest"]["status"] == "absent"
    assert payload["project_context"]["capability_registry"]["status"] == "absent"


def test_agent_schema_rejects_unknown_provider():
    schema = _load_json(CONTRACTS / "project-agent.schema.json")
    payload = _load_yaml(FIXTURES / "agent-frontmatter-valid.yaml")
    payload["providers"]["browser"] = {
        "required": False,
        "access": "read",
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)
