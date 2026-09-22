# PR Reviewer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Classificador Contabil PR Reviewer Agent as an independent read-only implementation auditor that owns Draft PR creation/update but never implementation or merge.

**Architecture:** The Agent binds the reusable `draft-pr` blueprint to the current project, gives observed branch state precedence over Execution Evidence, and routes findings by severity/classification. Git remains read-only while GitHub may be used to create or update the Draft PR.

**Tech Stack:** Markdown, YAML frontmatter, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/03-pr-reviewer-agent.md`

## Global Constraints

- HEAD, diff, and commits outrank Execution Evidence.
- Findings have severity `informational|warning|blocking` and classification `local|material`.
- Blocking local findings return to Issue Executor.
- Blocking material findings return to Task Reviewer.
- Draft PR creation/update is idempotent by head branch.
- An existing ready PR is never demoted.
- Merged/closed PRs are not reused or reopened.
- Pending CI keeps the PR draft; failed CI keeps it draft and adds a finding.
- The Agent never edits code, rewrites commits, marks ready, or merges.

## Review Focus

- Evidence that claims tests passed must not override a failing current check or contradictory diff.
- A pre-existing ready PR must be audited without being converted back to draft.
- Multiple PRs for the same head branch must fail closed rather than guessing which one is canonical.
- A local blocking defect must not trigger Task Review when the approved plan remains valid.
- A material implementation/spec mismatch must not be sent back as a simple code-fix loop.

---

### Task 1: Add the canonical PR Reviewer Agent definition

**Files:**
- Create: `.agents/agents/pr-reviewer.md`
- Create: `tests/test_project_agent_pr_reviewer.py`

**Interfaces:**
- Consumes: `execution_plan`, `execution_evidence`, `project_context`.
- Produces: `findings`, `draft_pr`; normal gate is human review/merge.

- [ ] **Step 1: Write the failing structural test**

Create:

```python
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
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_pr_reviewer.py
```

Expected: FAIL because the Agent file does not exist.

- [ ] **Step 3: Create the Agent**

Create:

```markdown
---
id: pr-reviewer
project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil
blueprint: draft-pr
context:
  bootstrap: ../references/project-context-bootstrap.md
inputs:
  - execution_plan
  - execution_evidence
  - project_context
outputs:
  - findings
  - draft_pr
providers:
  github:
    required: true
    preferred: mcp
    fallback:
      - gh
  git:
    required: true
    access: read
  terminal:
    required: true
    access: read
handoff:
  next: human_review
  gate: human_review_merge
---

# PR Reviewer Agent — Classificador Contabil

Build a fresh Project Context Envelope and invoke `draft-pr` as an independent auditor of the current delivery.

Treat current HEAD, diff, commits, and available checks as observed truth. Execution Evidence is supporting context and never overrides contradictory branch state.

Review the approved Execution Plan, structured references, acceptance criteria, tests, commits, and unexpected changes. Classify each finding by severity (`informational`, `warning`, `blocking`) and by scope (`local`, `material`). A blocking local finding routes back to the Issue Executor; a blocking material finding routes back to the Task Reviewer.

When audit conditions pass, create or update the Draft PR idempotently by head branch. Never create a duplicate, demote a ready PR, reuse a merged/closed PR, or mark a PR ready. Pending CI leaves the PR draft; failed CI leaves it draft and records a finding.

Never edit implementation files, fix code, rewrite commits, or merge. Stop at the human review/merge gate.
```

- [ ] **Step 4: Run the structural test**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_pr_reviewer.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .agents/agents/pr-reviewer.md tests/test_project_agent_pr_reviewer.py
git commit -m "feat(agents): add pr reviewer agent"
```

### Task 2: Pin audit precedence and finding routing

**Files:**
- Modify: `tests/test_project_agent_pr_reviewer.py`

**Interfaces:**
- Consumes: PR Reviewer body.
- Produces: guardrail tests for observed-state precedence, Draft PR idempotency, and routing.

- [ ] **Step 1: Add body regression tests**

Append:

```python
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
```

- [ ] **Step 2: Add idempotency assertions**

Append:

```python
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
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
./venv/bin/python -m pytest -q   tests/test_project_agents_foundation.py   tests/test_project_agent_pr_reviewer.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .agents/agents/pr-reviewer.md tests/test_project_agent_pr_reviewer.py
git commit -m "test(agents): pin pr reviewer audit guards"
```
