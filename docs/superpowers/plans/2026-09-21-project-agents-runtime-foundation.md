# Project Agents Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the project-local contracts and bootstrap reference that let thin Classificador Contabil Agents prove project context before invoking reusable Skill blueprints.

**Architecture:** Keep the runtime foundation declarative: JSON Schema validates Agent frontmatter and the in-memory Project Context Envelope, while a Markdown bootstrap reference defines discovery and fail-closed behavior. Reuse the repository's existing pytest + PyYAML + jsonschema stack; do not create an Agent runner, state store, or orchestration service.

**Tech Stack:** Markdown, YAML frontmatter, JSON Schema Draft 2020-12, Python 3, pytest, PyYAML 6.0.3, jsonschema 4.25.1.

**Spec:** `docs/specs/project-agents/00-runtime-foundation.md`

## Global Constraints

- New Agents do not replace or alter the current operational agentic pipeline.
- Agent definitions are canonical Markdown files and remain tool-agnostic.
- No automatic chaining between Agents.
- Runtime context is reconstructed for every invocation and is never persisted under `.agents/runs`, `.agents/state`, or `.agents/handoffs`.
- Project identity must be verified before any blueprint runs.
- Git/GitHub plus approved contracts remain the material source of truth; handoffs are transport, not state.
- `.agents/local/` is optional runtime-local configuration and must not be required for discovery mode. Its versioning/ignore policy is deliberately deferred.
- Do not add Cursor, Codex, or Trae adapters in this delivery.
- Do not modify `.github/agent-protocol.json`, existing `.agents/skills/`, or current `agent:*` behavior.

## Review Focus

- A copied Agent file with the wrong repository identity must not pass unnoticed; validation/tests must pin the expected project binding used by all four Agents.
- A workspace with no Manifest or Capability Registry must still have a valid discovery-mode envelope rather than crashing on missing optional files.
- An inferred issue that cannot be confirmed must fail closed before a blueprint can run.
- An unverified repository must never produce a usable Project Context Envelope.
- Unknown frontmatter fields must be rejected so tool-specific or operational state cannot silently leak into the canonical Agent contract.

---

### Task 1: Define the canonical Project Agent frontmatter contract

**Files:**
- Create: `.agents/contracts/project-agent.schema.json`
- Create: `tests/fixtures/project_agents/agent-frontmatter-valid.yaml`
- Create: `tests/fixtures/project_agents/agent-frontmatter-invalid-extra-field.yaml`
- Create: `tests/test_project_agents_foundation.py`

**Interfaces:**
- Consumes: YAML frontmatter parsed as `dict[str, object]`.
- Produces: Draft 2020-12 schema `.agents/contracts/project-agent.schema.json` validating `id`, `project`, `blueprint`, `context`, `inputs`, `outputs`, `providers`, and `handoff`.

- [ ] **Step 1: Write the failing schema tests**

Add the initial test module:

```python
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
```

Create the valid fixture:

```yaml
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
```

Create the invalid fixture with one forbidden field:

```yaml
id: task-reviewer
project:
  id: classificador-conta-contabil
  repository: Lucassribeiro9/classificador-conta-contabil
blueprint: task-review
context:
  bootstrap: ../references/project-context-bootstrap.md
inputs: [issue, project_context]
outputs: [review_report, execution_plan]
providers:
  github:
    required: true
    preferred: mcp
    fallback: [gh]
  git:
    required: true
    access: read
  terminal:
    required: true
    access: read
handoff:
  next: issue-executor
  gate: human_approval
runtime_state_file: .agents/state/current.json
```

- [ ] **Step 2: Run the tests and verify the schema is missing**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: FAIL because `.agents/contracts/project-agent.schema.json` does not exist.

- [ ] **Step 3: Add the minimal Project Agent schema**

Create `.agents/contracts/project-agent.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "project-agent.schema.json",
  "title": "Project Agent Definition",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "id",
    "project",
    "blueprint",
    "context",
    "inputs",
    "outputs",
    "providers",
    "handoff"
  ],
  "properties": {
    "id": {
      "type": "string",
      "enum": [
        "task-reviewer",
        "issue-executor",
        "pr-reviewer",
        "delivery-closer"
      ]
    },
    "project": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "repository"],
      "properties": {
        "id": {
          "type": "string",
          "minLength": 1
        },
        "repository": {
          "type": "string",
          "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
        }
      }
    },
    "blueprint": {
      "type": "string",
      "enum": [
        "task-review",
        "execute-issue",
        "draft-pr",
        "close-delivery"
      ]
    },
    "context": {
      "type": "object",
      "additionalProperties": false,
      "required": ["bootstrap"],
      "properties": {
        "bootstrap": {
          "type": "string",
          "const": "../references/project-context-bootstrap.md"
        }
      }
    },
    "inputs": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "outputs": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "providers": {
      "type": "object",
      "additionalProperties": false,
      "required": ["github", "git", "terminal"],
      "properties": {
        "github": {
          "type": "object",
          "additionalProperties": false,
          "required": ["required", "preferred", "fallback"],
          "properties": {
            "required": {"type": "boolean"},
            "preferred": {"type": "string", "enum": ["mcp"]},
            "fallback": {
              "type": "array",
              "uniqueItems": true,
              "items": {"type": "string", "enum": ["gh"]}
            }
          }
        },
        "git": {
          "$ref": "#/$defs/localProvider"
        },
        "terminal": {
          "$ref": "#/$defs/localProvider"
        }
      }
    },
    "handoff": {
      "type": "object",
      "additionalProperties": false,
      "required": ["next", "gate"],
      "properties": {
        "next": {
          "type": ["string", "null"],
          "enum": [
            "issue-executor",
            "pr-reviewer",
            "human_review",
            null
          ]
        },
        "gate": {
          "type": "string",
          "enum": [
            "human_approval",
            "human_review_merge",
            "none"
          ]
        }
      }
    }
  },
  "$defs": {
    "localProvider": {
      "type": "object",
      "additionalProperties": false,
      "required": ["required", "access"],
      "properties": {
        "required": {"type": "boolean"},
        "access": {
          "type": "string",
          "enum": ["read", "write"]
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run the focused tests**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: PASS for both initial schema tests.

- [ ] **Step 5: Commit the contract**

```bash
git add .agents/contracts/project-agent.schema.json tests/fixtures/project_agents tests/test_project_agents_foundation.py
git commit -m "feat(agents): add project agent contract"
```

### Task 2: Define the Project Context Envelope contract

**Files:**
- Create: `.agents/contracts/project-context-envelope.schema.json`
- Create: `tests/fixtures/project_agents/context-main-valid.json`
- Create: `tests/fixtures/project_agents/context-worktree-valid.json`
- Create: `tests/fixtures/project_agents/context-invalid-unverified.json`
- Modify: `tests/test_project_agents_foundation.py`

**Interfaces:**
- Consumes: a verified runtime snapshot under `project_context`.
- Produces: a schema that accepts only verified repository/issue context and models optional Manifest/Registry discovery status without persisting runtime state.

- [ ] **Step 1: Add failing envelope tests**

Append:

```python
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
```

Use this valid main fixture:

```json
{
  "schema_version": "1.0",
  "project_context": {
    "repository": {
      "root": "/workspace/classificador-conta-contabil",
      "identity": "Lucassribeiro9/classificador-conta-contabil",
      "verification": {
        "status": "verified",
        "confidence": "high",
        "sources": ["git_remote"]
      }
    },
    "issue": {
      "id": 519,
      "source": "explicit",
      "verified": true
    },
    "workspace": {
      "type": "main",
      "branch": "main"
    },
    "manifest": {
      "path": ".agents/local/project-manifest.yaml",
      "status": "absent"
    },
    "capability_registry": {
      "path": ".agents/local/capability-registry.yaml",
      "status": "absent"
    },
    "providers": {
      "github": "mcp",
      "git": "available",
      "terminal": "available"
    }
  }
}
```

For the worktree fixture, change `workspace.type` to `worktree`, branch to `feat/519-example`, set `issue.source` to `inferred`, and set Manifest/Registry status to `present`.

For the invalid fixture, copy the main fixture and set `repository.verification.status` to `unverified`.

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: FAIL because the context schema is missing.

- [ ] **Step 3: Add the envelope schema**

Create `.agents/contracts/project-context-envelope.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "project-context-envelope.schema.json",
  "title": "Project Context Envelope",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "project_context"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0"
    },
    "project_context": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "repository",
        "issue",
        "workspace",
        "manifest",
        "capability_registry",
        "providers"
      ],
      "properties": {
        "repository": {
          "type": "object",
          "additionalProperties": false,
          "required": ["root", "identity", "verification"],
          "properties": {
            "root": {"type": "string", "minLength": 1},
            "identity": {
              "type": "string",
              "pattern": "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
            },
            "verification": {
              "type": "object",
              "additionalProperties": false,
              "required": ["status", "confidence", "sources"],
              "properties": {
                "status": {"const": "verified"},
                "confidence": {
                  "type": "string",
                  "enum": ["high", "medium"]
                },
                "sources": {
                  "type": "array",
                  "minItems": 1,
                  "uniqueItems": true,
                  "items": {
                    "type": "string",
                    "enum": [
                      "git_remote",
                      "github",
                      "project_manifest",
                      "repository_structure"
                    ]
                  }
                }
              }
            }
          }
        },
        "issue": {
          "type": "object",
          "additionalProperties": false,
          "required": ["id", "source", "verified"],
          "properties": {
            "id": {"type": "integer", "minimum": 1},
            "source": {
              "type": "string",
              "enum": ["explicit", "inferred"]
            },
            "verified": {"const": true}
          }
        },
        "workspace": {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "branch"],
          "properties": {
            "type": {
              "type": "string",
              "enum": ["main", "worktree"]
            },
            "branch": {"type": "string", "minLength": 1}
          }
        },
        "manifest": {
          "$ref": "#/$defs/localSource"
        },
        "capability_registry": {
          "$ref": "#/$defs/localSource"
        },
        "providers": {
          "type": "object",
          "additionalProperties": false,
          "required": ["github", "git", "terminal"],
          "properties": {
            "github": {
              "type": "string",
              "enum": ["mcp", "gh", "unavailable"]
            },
            "git": {
              "type": "string",
              "enum": ["available", "unavailable"]
            },
            "terminal": {
              "type": "string",
              "enum": ["available", "unavailable"]
            }
          }
        }
      }
    }
  },
  "$defs": {
    "localSource": {
      "type": "object",
      "additionalProperties": false,
      "required": ["path", "status"],
      "properties": {
        "path": {"type": "string", "minLength": 1},
        "status": {
          "type": "string",
          "enum": ["present", "absent", "invalid"]
        }
      }
    }
  }
}
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: PASS.

- [ ] **Step 5: Commit the context contract**

```bash
git add .agents/contracts/project-context-envelope.schema.json tests/fixtures/project_agents tests/test_project_agents_foundation.py
git commit -m "feat(agents): add project context envelope contract"
```

### Task 3: Add the shared bootstrap reference and fail-closed policy

**Files:**
- Create: `.agents/references/project-context-bootstrap.md`
- Modify: `tests/test_project_agents_foundation.py`

**Interfaces:**
- Consumes: explicit repository/issue overrides plus observable Git/GitHub/workspace context.
- Produces: either a verified in-memory Project Context Envelope or a structured stop reason before blueprint invocation.

- [ ] **Step 1: Add failing bootstrap-content tests**

Append:

```python
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


- [ ] **Step 2: Run the tests and verify failure**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: FAIL because the bootstrap reference and ignore rule are absent.

- [ ] **Step 3: Add the bootstrap reference**

Create `.agents/references/project-context-bootstrap.md` with these exact sections and rules:

```markdown
# Project Context Bootstrap

## Purpose

Resolve the current repository, workspace, issue, local project sources, and available providers before a project-specific Agent invokes its reusable Skill blueprint.

The bootstrap is context discovery only. It never implements issue work, changes GitHub state, or persists runtime state.

## Resolution order

1. Apply an explicit repository or issue override when the invocation provides one.
2. Discover the repository root with `git rev-parse --show-toplevel`.
3. Detect whether the current workspace is the main checkout or a Git worktree and capture the active branch.
4. Verify project identity.
5. Locate `.agents/local/project-manifest.yaml` and `.agents/local/capability-registry.yaml`.
6. Resolve and verify the issue.
7. Detect GitHub, Git, and terminal providers.
8. Build the Project Context Envelope in memory.
9. Invoke the Agent blueprint only after all required verification gates pass.

## Project identity

Prefer evidence in this order:

1. git remote / GitHub repository identity;
2. Project Manifest identity;
3. repository structure evidence.

A different physical path or worktree does not change the logical repository identity.

If identity cannot be proven, stop with `project_identity_unverified`. Absence of evidence is never treated as a match.

## Local project sources

The Manifest and Capability Registry are optional. When either file is absent, record `status: absent` and continue in discovery mode.

An invalid present file is not equivalent to absence. Record `status: invalid` and let the consuming Agent decide whether its blueprint can continue.

## Issue resolution

Prefer an explicit issue number or URL.

When no issue is explicit, a branch/worktree name may produce one candidate issue number. Verify that candidate against GitHub and the current repository before using it.

If the candidate cannot be verified, stop with `issue_required`. Never broaden issue inference to unrelated open issues.

## Providers

Prefer GitHub MCP/API, then `gh` when a blueprint permits fallback. Git is authoritative only for local Git facts.

Record unavailable providers in the envelope rather than inventing availability.

## Runtime state

Build the Project Context Envelope in memory for the current invocation. Never persist it under `.agents/runs`, `.agents/state`, `.agents/handoffs`, or another hidden runtime state path.
```

- [ ] **Step 4: Preserve the deferred tracking policy**

Do not modify `.gitignore` for `.agents/local/`, `.agents/agents/`, `.agents/contracts/`, or `.agents/references/` in this delivery. The tracking policy remains a separate future decision.

- [ ] **Step 5: Run the focused and existing agentic tests**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py tests/test_agent_delivery_skills.py tests/test_agent_protocol.py
```

Expected: PASS. Existing pipeline tests must remain unchanged.

- [ ] **Step 6: Commit the bootstrap foundation**

```bash
git add .agents/references/project-context-bootstrap.md tests/test_project_agents_foundation.py
git commit -m "feat(agents): add project context bootstrap"
```

### Task 4: Add schema edge-case coverage

**Files:**
- Modify: `tests/test_project_agents_foundation.py`
- Create: `tests/fixtures/project_agents/context-discovery-mode-valid.json`

**Interfaces:**
- Consumes: the schemas from Tasks 1-2.
- Produces: regression coverage for optional local sources, provider unavailability, and strict frontmatter validation.

- [ ] **Step 1: Add regression tests**

Append:

```python
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
```

Use the main valid context as the discovery-mode fixture, but set GitHub to `unavailable`, keep Git/terminal available, and keep Manifest/Registry absent. The envelope remains structurally valid; individual Agent provider requirements decide whether execution can proceed.

- [ ] **Step 2: Run the focused tests**

Run:

```bash
./venv/bin/python -m pytest -q tests/test_project_agents_foundation.py
```

Expected: PASS.

- [ ] **Step 3: Run the full non-PostgreSQL suite**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 4: Commit the edge-case coverage**

```bash
git add tests/test_project_agents_foundation.py tests/fixtures/project_agents
git commit -m "test(agents): cover runtime foundation edge cases"
```
