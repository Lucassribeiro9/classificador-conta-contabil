# Delivery Closer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Classificador Contabil Delivery Closer Agent as a post-merge cleanup wrapper around `close-delivery`.

**Architecture:** The Agent proves merge through GitHub-first evidence, updates main fast-forward-only, and performs cleanup in a safe order. It owns no merge or review decision and fails closed on dirty workspaces, unproven merge, or unsafe branch removal.

**Tech Stack:** Markdown, YAML frontmatter, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/04-delivery-closer-agent.md`

## Global Constraints

- Human merge is a prerequisite.
- GitHub MCP/API is preferred merge proof, `gh` is fallback, and local Git alone is insufficient for destructive cleanup.
- Require `merged=true`, a known `merge_commit_sha`, and that SHA in updated main.
- Main updates are fast-forward-only.
- Never auto-stash, reset, clean, discard, or force-remove dirty work.
- Remove worktree before local branch.
- Remote branch deletion must be safe and idempotent.
- Never close the issue manually to compensate for automation failure.
- The final state is `completed`; there is no next Agent.

## Review Focus

- Squash merge changes ancestry, so local branch deletion must rely on proven merge safety rather than naive `--merged` checks.
- A dirty worktree must block cleanup even when the PR is definitely merged.
- A remote branch already absent must be a no-op, not an error.
- A shared head branch with another active PR must prevent remote deletion.
- An open issue after merge must be reported accurately rather than manually closed.

---

### Task 1: Add the canonical Delivery Closer Agent definition

**Files:**
- Create: `.agents/agents/delivery-closer.md`
- Create: `tests/test_project_agent_delivery_closer.py`

**Interfaces:**
- Consumes: `pull_request`, `project_context`.
- Produces: `closure_result`; terminal handoff with no next Agent.

- [ ] **Step 1: Write the failing structural test**

Create:

```python
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
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_delivery_closer.py
```

Expected: FAIL because the Agent file is missing.

- [ ] **Step 3: Create the Agent**

Create:

```markdown
---
id: delivery-closer
project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil
blueprint: close-delivery
context:
  bootstrap: ../references/project-context-bootstrap.md
inputs:
  - pull_request
  - project_context
outputs:
  - closure_result
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
  next: null
  gate: none
---

# Delivery Closer Agent — Classificador Contabil

Build a fresh Project Context Envelope, resolve the unique target PR/issue, and invoke `close-delivery` only after human merge.

Prefer GitHub MCP/API as authoritative merge proof and `gh` as fallback. Local Git is sufficient only for local facts. Destructive cleanup requires `merged=true`, a known `merge_commit_sha`, and that SHA present in the updated main branch.

Update main fast-forward-only. Never force, reset destructively, clean, auto-stash, discard local work, or force-remove a dirty worktree. Remove the worktree before the local branch. Remote branch deletion is a no-op when already absent and is blocked when another active PR shares the same head.

Verify whether the issue closed through the expected merge relationship such as `Closes #...`. Never close the issue manually as compensation.

Finish with `completed` only when safe closure checks are satisfied. There is no next Agent.
```

- [ ] **Step 4: Run the structural test**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_delivery_closer.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .agents/agents/delivery-closer.md tests/test_project_agent_delivery_closer.py
git commit -m "feat(agents): add delivery closer agent"
```

### Task 2: Pin merge proof and cleanup safety

**Files:**
- Modify: `tests/test_project_agent_delivery_closer.py`

**Interfaces:**
- Consumes: Delivery Closer body.
- Produces: regression checks for proof hierarchy, safe cleanup order, dirty-workspace blocking, and terminal completion.

- [ ] **Step 1: Add merge-proof assertions**

Append:

```python
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
```

- [ ] **Step 2: Add cleanup guard assertions**

Append:

```python
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
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
./venv/bin/python -m pytest -q   tests/test_project_agents_foundation.py   tests/test_project_agent_delivery_closer.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add .agents/agents/delivery-closer.md tests/test_project_agent_delivery_closer.py
git commit -m "test(agents): pin delivery closer safety"
```
