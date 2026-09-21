# Issue Executor Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Classificador Contabil Issue Executor Agent as a thin wrapper around `execute-issue`, consuming only an explicitly approved Execution Plan.

**Architecture:** The Agent delegates implementation behavior to the reusable blueprint and adds only project binding, bootstrap, provider permissions, approved-plan authority, and local-vs-material deviation routing. Tests verify that write-capable providers are declared without copying execution procedure into the Agent.

**Tech Stack:** Markdown, YAML frontmatter, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/02-issue-executor-agent.md`

## Global Constraints

- An explicitly approved Execution Plan is required.
- The Execution Plan is the planning authority; the Agent must not silently replan.
- Capabilities and references are lightly revalidated at runtime, not rediscovered from scratch.
- Moved-but-equivalent references are local deviations; semantically invalid assumptions are material deviations.
- Material deviation returns `needs_re_review` to Task Reviewer.
- Required stages cannot be skipped.
- TDD applies when the approved plan requires it.
- Scope cannot expand.
- No force push, merge, or Draft PR creation as a substitute for PR Reviewer.

## Review Focus

- A plan that exists but has no proof of human approval must not execute.
- A moved reference must not be misclassified as material when its semantic source remains unchanged.
- A semantically changed spec at the same path must still trigger material re-review.
- A recommended stage that cannot run must be evidenced as skipped rather than silently treated as completed.
- Repair attempts must remain bounded and cause-aware so repeated blind retries cannot hide a failing delivery.

---

### Task 1: Add the canonical Issue Executor Agent definition

**Files:**
- Create: `.agents/agents/issue-executor.md`
- Create: `tests/test_project_agent_issue_executor.py`

**Interfaces:**
- Consumes: `execution_plan`, `project_context`.
- Produces: `execution_evidence`; normal handoff to `pr-reviewer`, material deviation handoff back to `task-reviewer`.

- [ ] **Step 1: Write the failing structural test**

Create:

```python
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
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_issue_executor.py
```

Expected: FAIL because the Agent file is missing.

- [ ] **Step 3: Create the thin Agent**

Create:

```markdown
---
id: issue-executor
project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil
blueprint: execute-issue
context:
  bootstrap: ../references/project-context-bootstrap.md
inputs:
  - execution_plan
  - project_context
outputs:
  - execution_evidence
providers:
  github:
    required: true
    preferred: mcp
    fallback:
      - gh
  git:
    required: true
    access: write
  terminal:
    required: true
    access: write
handoff:
  next: pr-reviewer
  gate: none
---

# Issue Executor Agent — Classificador Contabil

Build a fresh Project Context Envelope, then invoke `execute-issue` only for an explicitly approved Execution Plan.

Treat the approved plan as the planning authority. Revalidate declared capabilities and references before use without repeating the Task Review. A reference that moved without semantic change is a local deviation and must be evidenced. A changed contract, invalid premise, scope change, or architectural decision is a material deviation: stop with `needs_re_review` and route back to the Task Reviewer.

Execute only the approved stage DAG. Required stages are never skipped; recommended stages may be skipped only with objective evidence. Resolve capabilities through the Capability Registry when present and discovery fallback when absent. Apply TDD when required by the plan, keep repairs bounded, create semantic commits, and perform only the final approved push.

Produce Execution Evidence and stop. Never widen scope, force push, merge, create the Draft PR in place of the PR Reviewer, or continue after a material deviation.
```

- [ ] **Step 4: Run the structural test**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_issue_executor.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .agents/agents/issue-executor.md tests/test_project_agent_issue_executor.py
git commit -m "feat(agents): add issue executor agent"
```

### Task 2: Pin approved-plan and deviation boundaries

**Files:**
- Modify: `tests/test_project_agent_issue_executor.py`

**Interfaces:**
- Consumes: Issue Executor body.
- Produces: regression tests that preserve approved-plan authority and routing boundaries.

- [ ] **Step 1: Add body guardrail tests**

Append:

```python
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
```

- [ ] **Step 2: Add project binding and provider assertions**

Append:

```python
def test_issue_executor_has_only_expected_project_and_provider_permissions():
    metadata, _ = _load_agent()

    assert metadata["project"]["repository"] == (
        "Lucassribeiro9/classificador-conta-contabil"
    )
    assert set(metadata["providers"]) == {"github", "git", "terminal"}
    assert metadata["providers"]["github"]["preferred"] == "mcp"
    assert metadata["providers"]["github"]["fallback"] == ["gh"]
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
./venv/bin/python -m pytest -q   tests/test_project_agents_foundation.py   tests/test_project_agent_issue_executor.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .agents/agents/issue-executor.md tests/test_project_agent_issue_executor.py
git commit -m "test(agents): pin issue executor boundaries"
```
