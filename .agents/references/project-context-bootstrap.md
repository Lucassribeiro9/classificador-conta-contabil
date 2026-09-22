# Project Context Bootstrap

## Purpose

Resolve the current repository, workspace, issue, local project sources, and available providers before a project-specific Agent invokes its reusable Skill blueprint.

The bootstrap is context discovery only. It never implements issue work, changes GitHub state, or persists runtime state.

## Resolution order

1. Apply an explicit override for repository or issue when the invocation provides one.
2. Discover the repository root with `git rev-parse --show-toplevel`.
3. Detect whether the current workspace is the main checkout or a Git worktree and capture the active branch.
4. Verify project identity from git remote / GitHub evidence first.
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

Build the Project Context Envelope in memory for the current invocation; never persist it under `.agents/runs`, `.agents/state`, `.agents/handoffs`, or another hidden runtime state path.
