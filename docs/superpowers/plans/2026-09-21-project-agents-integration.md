# Project Agents Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the four Classificador Contabil Agents as one non-automatic delivery protocol without integrating them into the current operational agentic pipeline.

**Architecture:** Integration remains contract-level: parse all four Agent definitions, validate them with the shared schema, assert the handoff chain and human gates, and use sanitized fixtures for happy-path and material-deviation routing. Update the project Agent catalog only after the complete layer exists.

**Tech Stack:** Markdown, YAML, JSON, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/00-runtime-foundation.md`, plus `01-task-reviewer-agent.md`, `02-issue-executor-agent.md`, `03-pr-reviewer-agent.md`, and `04-delivery-closer-agent.md`.

## Global Constraints

- The new Agents remain independent from the current `issue-delivery-loop`.
- No automatic chaining is introduced.
- Human approval remains between Task Reviewer and Executor.
- Human review/merge remains between PR Reviewer and Delivery Closer.
- Runtime state is not persisted.
- All four Agents bind to the same Classificador repository identity.
- Existing local Skills, contracts, labels, and `.github/agent-protocol.json` remain unchanged.
- This plan validates future compatibility; it does not perform current-pipeline migration.

## Review Focus

- The chain must not accidentally bypass the two human gates when represented as data.
- A material deviation must route to Task Reviewer rather than directly back to Executor.
- All four Agents must share one exact project identity and bootstrap path.
- The project README must not imply the new Agents are operationally wired into the existing pipeline.
- Existing agentic regression tests must continue to pass unchanged after the new catalog entries are added.

---

### Task 1: Add cross-Agent contract validation

**Files:**
- Create: `tests/test_project_agents_integration.py`

**Interfaces:**
- Consumes: all four `.agents/agents/*.md` definitions and `project-agent.schema.json`.
- Produces: one regression suite proving uniqueness, shared binding, shared bootstrap, blueprint mapping, and canonical normal handoffs.

- [ ] **Step 1: Write the integration test**

Create:

```python
import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = ROOT / ".agents/agents"
SCHEMA_PATH = ROOT / ".agents/contracts/project-agent.schema.json"

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
```

- [ ] **Step 2: Run and verify the full Agent set**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_integration.py
```

Expected: PASS only when all four prior plans have been implemented.

- [ ] **Step 3: Commit**

```bash
git add tests/test_project_agents_integration.py
git commit -m "test(agents): validate project agent chain"
```

### Task 2: Add sanitized happy-path and re-review handoff fixtures

**Files:**
- Create: `tests/fixtures/project_agents/happy-path-handoffs.json`
- Create: `tests/fixtures/project_agents/material-deviation-handoffs.json`
- Modify: `tests/test_project_agents_integration.py`

**Interfaces:**
- Consumes: conceptual structured handoffs from the approved design.
- Produces: sanitized fixtures proving human gates and material-deviation routing without introducing runtime state persistence.

- [ ] **Step 1: Create the happy-path fixture**

```json
{
  "issue": 519,
  "steps": [
    {
      "current_agent": "task-reviewer",
      "status": "ready",
      "next_agent": "issue-executor",
      "gate": "human_approval"
    },
    {
      "current_agent": "issue-executor",
      "status": "ready",
      "next_agent": "pr-reviewer",
      "gate": "none"
    },
    {
      "current_agent": "pr-reviewer",
      "status": "ready",
      "next_agent": "human_review",
      "gate": "human_review_merge"
    },
    {
      "current_agent": "delivery-closer",
      "status": "completed",
      "next_agent": null,
      "gate": "none"
    }
  ]
}
```

- [ ] **Step 2: Create the material-deviation fixture**

```json
{
  "issue": 519,
  "steps": [
    {
      "current_agent": "task-reviewer",
      "revision": 1,
      "status": "ready",
      "next_agent": "issue-executor"
    },
    {
      "current_agent": "issue-executor",
      "status": "needs_re_review",
      "reason": "material_deviation",
      "next_agent": "task-reviewer"
    },
    {
      "current_agent": "task-reviewer",
      "revision": 2,
      "status": "ready",
      "next_agent": "issue-executor"
    }
  ]
}
```

- [ ] **Step 3: Add fixture-routing tests**

Append:

```python
FIXTURES = ROOT / "tests/fixtures/project_agents"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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
```

- [ ] **Step 4: Run integration tests**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_integration.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/project_agents tests/test_project_agents_integration.py
git commit -m "test(agents): cover project agent handoffs"
```

### Task 3: Document the new layer without changing current pipeline semantics

**Files:**
- Modify: `.agents/README.md`
- Modify: `tests/test_project_agents_integration.py`

**Interfaces:**
- Consumes: completed project Agent layer.
- Produces: catalog documentation that clearly marks the four Agents as future/isolated and leaves existing Skills/issue-delivery-loop operational semantics intact.

- [ ] **Step 1: Add the failing catalog test**

Append:

```python
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
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_integration.py
```

Expected: FAIL because the catalog has not been updated.

- [ ] **Step 3: Add the catalog section**

Append to `.agents/README.md`:

```markdown
## Project Agents

O projeto também possui uma camada canônica de Project Agents preparada para validação isolada e integração futura:

- `task-reviewer` → blueprint `task-review`;
- `issue-executor` → blueprint `execute-issue`;
- `pr-reviewer` → blueprint `draft-pr`;
- `delivery-closer` → blueprint `close-delivery`.

As definições ficam em `.agents/agents/`, usam
`.agents/contracts/project-agent.schema.json`,
`.agents/contracts/project-context-envelope.schema.json` e
`.agents/references/project-context-bootstrap.md`.

Esses Project Agents não fazem parte da operação atual e não substituem o
`issue-delivery-loop`, as Skills locais ou o protocolo GitHub vigente. A
integração futura com a esteira supervisionada exige issue própria.
```

- [ ] **Step 4: Run all Agent tests**

Run:

```bash
./venv/bin/python -m pytest -q   tests/test_project_agents_foundation.py   tests/test_project_agent_task_reviewer.py   tests/test_project_agent_issue_executor.py   tests/test_project_agent_pr_reviewer.py   tests/test_project_agent_delivery_closer.py   tests/test_project_agents_integration.py   tests/test_agent_delivery_skills.py   tests/test_agent_protocol.py
```

Expected: PASS.

- [ ] **Step 5: Run the full non-PostgreSQL suite**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 6: Commit the catalog integration**

```bash
git add .agents/README.md tests/test_project_agents_integration.py
git commit -m "docs(agents): catalog project agent layer"
```
