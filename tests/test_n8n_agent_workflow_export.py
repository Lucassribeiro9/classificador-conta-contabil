from __future__ import annotations

import json
from pathlib import Path

WORKFLOW = Path("n8n/workflows/agent-documental-pilot.sanitized.json")
FIXTURE_DIR = Path("n8n/fixtures/agent-documental-pilot")
FORBIDDEN_SNIPPETS = (
    "ghp_",
    "http://localhost",
    "https://",
    "ngrok",
    "token",
    "credentialId",
    "executionData",
    "/home/",
    "/tmp/",
)


def test_agent_documental_workflow_export_is_sanitized_and_versioned():
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    raw = WORKFLOW.read_text(encoding="utf-8")

    assert workflow["name"] == "Agent Documental Pilot"
    assert workflow["active"] is False
    assert workflow["version"] == "sanitized-1"
    assert "__PRIVATE_RUNNER_URL__" in raw
    assert "__GITHUB_CREDENTIAL_PLACEHOLDER__" in raw
    assert "__N8N_DATA_TABLE_ID__" in raw
    assert "__RUNNER_HMAC_SECRET__" in raw
    assert all(snippet not in raw for snippet in FORBIDDEN_SNIPPETS)

    node_types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.webhook" in node_types
    assert "n8n-nodes-base.httpRequest" in node_types
    assert "n8n-nodes-base.code" in node_types
    assert "n8n-nodes-base.dataTable" in node_types
    assert "n8n-nodes-base.respondToWebhook" in node_types


def test_agent_documental_workflow_fixtures_cover_acceptance_scenarios():
    expected = {
        "evento-autorizado.json",
        "evento-duplicado.json",
        "github-divergente.json",
        "runner-indisponivel.json",
    }
    existing = {path.name for path in FIXTURE_DIR.glob("*.json")}

    assert expected <= existing
    for fixture_name in expected:
        fixture = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
        assert fixture["repository"] == "Lucassribeiro9/classificador-conta-contabil"
        assert fixture["issue_number"] == 378
        assert "event_id" in fixture
        assert "expected_state" in fixture
        assert "secret" not in json.dumps(fixture).lower()
