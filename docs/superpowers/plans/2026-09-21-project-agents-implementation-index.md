# Project Agents Implementation Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Coordinate implementation of the approved Classificador Contabil Project Agent layer without changing the current operational agentic pipeline.

**Architecture:** Implement shared contracts/bootstrap first, then each thin Agent independently, and finish with cross-Agent integration tests and catalog documentation. Each plan is independently reviewable; later plans depend only on explicit contracts created by earlier ones.

**Tech Stack:** Markdown, YAML, JSON, JSON Schema Draft 2020-12, Python, pytest, PyYAML, jsonschema.

**Spec:** `docs/specs/project-agents/00-runtime-foundation.md` and `docs/specs/project-agents/01-04-*.md`.

## Global Constraints

- Do not integrate with the current operational `issue-delivery-loop` in this delivery.
- Do not modify `.github/agent-protocol.json` or current `agent:*` semantics.
- Keep all four Agents thin and tool-agnostic.
- Do not create runtime state directories or automatic Agent chaining.
- Preserve the two human gates: approval before execution and review/merge before closure.
- Keep project-local configuration under `.agents/local/` optional; defer its final versioning/ignore policy.
- No new runtime dependency is required.

## Review Focus

- Do not let later Agent plans duplicate the shared bootstrap or schemas.
- Do not accidentally make the new layer operational in the existing pipeline through README/routing changes.
- Keep provider permissions minimal for each role.
- Preserve exact Agent IDs/blueprint mappings across all plans.
- Run existing agentic regression tests after integration to prove coexistence.

---

## Execution Order

1. `2026-09-21-project-agents-runtime-foundation.md`
2. `2026-09-21-task-reviewer-agent.md`
3. `2026-09-21-issue-executor-agent.md`
4. `2026-09-21-pr-reviewer-agent.md`
5. `2026-09-21-delivery-closer-agent.md`
6. `2026-09-21-project-agents-integration.md`

## Dependency Map

```text
Runtime Foundation
├── project-agent.schema.json
├── project-context-envelope.schema.json
└── project-context-bootstrap.md
        ↓
Task Reviewer Agent
        ↓
Issue Executor Agent
        ↓
PR Reviewer Agent
        ↓
Delivery Closer Agent
        ↓
Integration / regression gate
```

The linear order is intentional for implementation review, even though the four Agent definition files are otherwise loosely coupled. Each Agent plan must pass its focused tests before the next plan begins.

## Completion Gate

The layer is complete only when:

- both shared schemas validate;
- the bootstrap reference and optional local-source discovery behavior are covered by tests;
- all four Agent definitions validate against the shared schema;
- every Agent uses the exact Classificador repository binding;
- normal handoffs preserve the two human gates;
- material deviation routes from Executor to Task Reviewer;
- no Agent auto-invokes the next;
- the existing agentic tests remain green;
- `make test` passes.
