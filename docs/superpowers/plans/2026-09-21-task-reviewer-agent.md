# Task Reviewer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Classificador Contabil Task Reviewer Agent as a thin project-bound wrapper around the reusable `task-review` blueprint.

**Architecture:** The Agent is a Markdown definition with schema-validated frontmatter and a short body that loads project context, preserves observed repository reality, and delegates planning behavior to `task-review`. Tests inspect both structure and guardrails; they do not reimplement the blueprint.

**Tech Stack:** Markdown, YAML frontmatter, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/01-task-reviewer-agent.md`

## Global Constraints

- The Agent must remain thin; `task-review` is the behavioral source of truth.
- It must bind to `Lucassribeiro9/classificador-conta-contabil`.
- It must run the shared Project Context Bootstrap before the blueprint.
- It must not implement, create branch/worktree, modify code, or create a PR.
- It must discover real PRD/spec/architecture/code references rather than invent fixed paths.
- Path drift alone is not blocking.
- Only material ambiguity may require a human question.
- Successful output is Review Report + Execution Plan 1.1 with structured `capabilities` and `references`.
- The final gate is human approval; there is no automatic Executor invocation.

## Review Focus

- A missing expected spec path with a valid spec elsewhere must be treated as drift, not as absence.
- Multiple plausible specs must not be selected arbitrarily when issue/PRD/history cannot disambiguate them.
- Declared stack and observed stack must remain distinguishable so stale documentation cannot overwrite repository reality.
- A Task Review that needs no spec must be able to return `not_needed` without inventing one.
- The Agent file must not copy detailed Task Review procedure from the blueprint.

---

### Task 1: Add the canonical Task Reviewer Agent definition

**Files:**
- Create: `.agents/agents/task-reviewer.md`
- Create: `tests/test_project_agent_task_reviewer.py`

**Interfaces:**
- Consumes: explicit/inferred verified issue, Project Context Envelope, optional Manifest/Registry, repository sources.
- Produces: `review_report`, `execution_plan`; handoff to `issue-executor` behind `human_approval`.

- [ ] **Step 1: Write the failing structural test**

Create:

```python
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
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_task_reviewer.py
```

Expected: FAIL because `.agents/agents/task-reviewer.md` does not exist.

- [ ] **Step 3: Create the thin Agent definition**

Create:

```markdown
---
id: task-reviewer
project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil
blueprint: task-review
context:
  bootstrap: ../references/project-context-bootstrap.md
inputs:
  - issue
  - project_context
outputs:
  - review_report
  - execution_plan
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
  next: issue-executor
  gate: human_approval
---

# Task Reviewer Agent — Classificador Contabil

Build the Project Context Envelope before invoking `task-review`.

Use the verified repository and issue as the boundary of the review. Treat the repository's observed stack as evidence; do not replace it with a preferred stack or stale declared stack.

Discover applicable PRD, specs, architecture, tests, and implementation sources from the repository. An expected path that moved is drift, not proof that the source does not exist. Resolve multiple plausible sources from issue scope, PRD, history, and repository evidence; ask the human only when a material ambiguity remains.

The Execution Plan must use schema version 1.1 and carry the capabilities and structured references required by downstream execution. The Agent does not duplicate domain knowledge; it records the sources that provide it.

Stop after producing the Review Report and Execution Plan. Never implement, create a branch or worktree, modify tracked content, create a PR, or invoke the Issue Executor automatically.
```

- [ ] **Step 4: Run the structural test**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_task_reviewer.py
```

Expected: PASS.

- [ ] **Step 5: Commit the Agent**

```bash
git add .agents/agents/task-reviewer.md tests/test_project_agent_task_reviewer.py
git commit -m "feat(agents): add task reviewer agent"
```

### Task 2: Pin Task Reviewer behavioral guardrails

**Files:**
- Modify: `tests/test_project_agent_task_reviewer.py`

**Interfaces:**
- Consumes: Task Reviewer Markdown body.
- Produces: regression checks that the project wrapper retains context-discovery rules while leaving procedure to the blueprint.

- [ ] **Step 1: Add failing body assertions**

Append:

```python
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
```

- [ ] **Step 2: Run the test**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agent_task_reviewer.py
```

Expected: PASS after the Task 1 body exists; if a guardrail phrase is missing, make the smallest wording correction in the Agent file.

- [ ] **Step 3: Add project-binding regression coverage**

Append:

```python
def test_task_reviewer_is_bound_to_classificador_repository():
    metadata, _ = _load_agent(AGENT_PATH)

    assert (
        metadata["project"]["repository"]
        == "Lucassribeiro9/classificador-conta-contabil"
    )
    assert metadata["context"]["bootstrap"] == (
        "../references/project-context-bootstrap.md"
    )
```

- [ ] **Step 4: Run focused and foundation tests**

Run:

```bash
./venv/bin/python -m pytest -q   tests/test_project_agents_foundation.py   tests/test_project_agent_task_reviewer.py
```

Expected: PASS.

- [ ] **Step 5: Commit the guardrails**

```bash
git add .agents/agents/task-reviewer.md tests/test_project_agent_task_reviewer.py
git commit -m "test(agents): pin task reviewer guardrails"
```
