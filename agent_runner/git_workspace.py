from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Protocol


class GitWorkspaceErrorCode:
    BASE_SHA_MISMATCH = "BASE_SHA_MISMATCH"
    WORKTREE_DIRTY = "WORKTREE_DIRTY"
    WORKTREE_INCOMPATIBLE = "WORKTREE_INCOMPATIBLE"
    OUT_OF_SCOPE_CHANGES = "OUT_OF_SCOPE_CHANGES"
    BRANCH_INCOMPATIBLE = "BRANCH_INCOMPATIBLE"
    PUSH_FAILED = "PUSH_FAILED"
    CLEANUP_NOT_SAFE = "CLEANUP_NOT_SAFE"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"


@dataclass(frozen=True)
class DraftPullRequestRequest:
    issue_number: int
    branch: str
    base_branch: str
    title: str
    body: str
    commit_sha: str | None


class DraftPublisher(Protocol):
    def create_draft(self, request: DraftPullRequestRequest) -> str: ...


@dataclass(frozen=True)
class GitWorkspaceRequest:
    issue_number: int
    execution_id: str
    branch: str
    base_branch: str
    base_sha: str
    allowed_paths: list[str]
    commit_message: str
    remote_name: str
    draft_title: str
    draft_body: str
    mutate: Callable[[Path], None] | None = None


@dataclass(frozen=True)
class GitWorkspaceResult:
    branch: str
    base_sha: str
    head_sha: str | None
    worktree_ref: str
    changed_files: list[str]
    commit_sha: str | None
    pushed: bool
    draft_requested: bool
    error_code: str | None = None


class GitWorkspaceManager:
    def __init__(
        self,
        *,
        repository_path: Path | str,
        worktrees_root: Path | str,
        draft_publisher: DraftPublisher,
        git_timeout_seconds: int = 15,
    ) -> None:
        self.repository_path = Path(repository_path).resolve()
        self.worktrees_root = Path(worktrees_root).resolve()
        self.draft_publisher = draft_publisher
        self.git_timeout_seconds = git_timeout_seconds
        self.worktrees_root.mkdir(parents=True, exist_ok=True)

    def prepare_publish_and_request_draft(
        self,
        request: GitWorkspaceRequest,
    ) -> GitWorkspaceResult:
        worktree_ref = _worktree_ref(request.issue_number, request.execution_id)
        worktree_path = self.worktrees_root / worktree_ref
        allowed_paths = _normalize_allowed_paths(request.allowed_paths)
        if allowed_paths is None:
            return self._result(request, worktree_ref, None, [], None, False, False, GitWorkspaceErrorCode.PATH_NOT_ALLOWED)

        if not self._commit_exists(request.base_sha):
            return self._result(request, worktree_ref, None, [], None, False, False, GitWorkspaceErrorCode.BASE_SHA_MISMATCH)

        branch_error = self._ensure_branch_compatible(request.branch, request.base_sha, allowed_paths)
        if branch_error is not None:
            return self._result(request, worktree_ref, None, [], None, False, False, branch_error)

        worktree_error = self._ensure_worktree(request.branch, request.base_sha, worktree_path)
        if worktree_error is not None:
            return self._result(request, worktree_ref, None, [], None, False, False, worktree_error)

        if request.mutate is not None:
            request.mutate(worktree_path)

        changed_files = self._changed_files(worktree_path)
        out_of_scope = [path for path in changed_files if path not in allowed_paths]
        if out_of_scope:
            return self._result(request, worktree_ref, None, changed_files, None, False, False, GitWorkspaceErrorCode.OUT_OF_SCOPE_CHANGES)
        if not changed_files:
            return self._result(request, worktree_ref, request.base_sha, [], None, False, False, None)

        self._git(worktree_path, "add", "--", *changed_files)
        self._git(worktree_path, "commit", "-m", request.commit_message)
        commit_sha = self._git(worktree_path, "rev-parse", "HEAD")

        try:
            self._git(worktree_path, "push", request.remote_name, f"HEAD:{request.branch}")
        except subprocess.CalledProcessError:
            return self._result(request, worktree_ref, commit_sha, changed_files, commit_sha, False, False, GitWorkspaceErrorCode.PUSH_FAILED)

        self.draft_publisher.create_draft(
            DraftPullRequestRequest(
                issue_number=request.issue_number,
                branch=request.branch,
                base_branch=request.base_branch,
                title=request.draft_title,
                body=request.draft_body,
                commit_sha=commit_sha,
            )
        )
        return self._result(request, worktree_ref, commit_sha, changed_files, commit_sha, True, True, None)

    def cleanup_execution(self, issue_number: int, execution_id: str) -> GitWorkspaceResult:
        worktree_ref = _worktree_ref(issue_number, execution_id)
        worktree_path = (self.worktrees_root / worktree_ref).resolve()
        if not _is_relative_to(worktree_path, self.worktrees_root):
            return GitWorkspaceResult("", "", None, worktree_ref, [], None, False, False, GitWorkspaceErrorCode.CLEANUP_NOT_SAFE)
        if not worktree_path.exists():
            return GitWorkspaceResult("", "", None, worktree_ref, [], None, False, False, None)
        if self._changed_files(worktree_path):
            return GitWorkspaceResult("", "", None, worktree_ref, self._changed_files(worktree_path), None, False, False, GitWorkspaceErrorCode.WORKTREE_DIRTY)
        self._git(self.repository_path, "worktree", "remove", str(worktree_path))
        return GitWorkspaceResult("", "", None, worktree_ref, [], None, False, False, None)

    def _ensure_worktree(self, branch: str, base_sha: str, worktree_path: Path) -> str | None:
        if worktree_path.exists():
            if not (worktree_path / ".git").exists():
                return GitWorkspaceErrorCode.WORKTREE_INCOMPATIBLE
            if self._changed_files(worktree_path):
                return GitWorkspaceErrorCode.WORKTREE_DIRTY
            current_branch = self._git(worktree_path, "branch", "--show-current")
            if current_branch != branch:
                return GitWorkspaceErrorCode.WORKTREE_INCOMPATIBLE
            return None
        self._git(self.repository_path, "worktree", "add", "-b", branch, str(worktree_path), base_sha)
        return None

    def _ensure_branch_compatible(self, branch: str, base_sha: str, allowed_paths: set[str]) -> str | None:
        if not self._ref_exists(branch):
            return None
        merge_base = self._git(self.repository_path, "merge-base", branch, base_sha)
        if merge_base != base_sha:
            return GitWorkspaceErrorCode.BRANCH_INCOMPATIBLE
        changed = self._git(self.repository_path, "diff", "--name-only", f"{base_sha}..{branch}")
        changed_files = [line for line in changed.splitlines() if line]
        if any(path not in allowed_paths for path in changed_files):
            return GitWorkspaceErrorCode.BRANCH_INCOMPATIBLE
        return None

    def _changed_files(self, cwd: Path) -> list[str]:
        output = self._git(cwd, "status", "--porcelain")
        paths: list[str] = []
        for line in output.splitlines():
            if not line:
                continue
            path = line[2:].lstrip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            paths.append(path)
        return sorted(paths)

    def _commit_exists(self, sha: str) -> bool:
        try:
            self._git(self.repository_path, "cat-file", "-e", f"{sha}^{{commit}}")
            return True
        except subprocess.CalledProcessError:
            return False

    def _ref_exists(self, ref: str) -> bool:
        try:
            self._git(self.repository_path, "rev-parse", "--verify", ref)
            return True
        except subprocess.CalledProcessError:
            return False

    def _git(self, cwd: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.git_timeout_seconds,
        )
        return completed.stdout.strip()

    def _result(
        self,
        request: GitWorkspaceRequest,
        worktree_ref: str,
        head_sha: str | None,
        changed_files: list[str],
        commit_sha: str | None,
        pushed: bool,
        draft_requested: bool,
        error_code: str | None,
    ) -> GitWorkspaceResult:
        return GitWorkspaceResult(
            branch=request.branch,
            base_sha=request.base_sha,
            head_sha=head_sha,
            worktree_ref=worktree_ref,
            changed_files=sorted(changed_files),
            commit_sha=commit_sha,
            pushed=pushed,
            draft_requested=draft_requested,
            error_code=error_code,
        )


def _normalize_allowed_paths(paths: list[str]) -> set[str] | None:
    normalized: set[str] = set()
    for value in paths:
        pure = PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts or str(pure) in {"", "."}:
            return None
        normalized.add(pure.as_posix())
    return normalized


def _worktree_ref(issue_number: int, execution_id: str) -> str:
    safe_execution = re.sub(r"[^a-z0-9_-]", "", execution_id.lower())[:11]
    return f"issue-{issue_number}-{safe_execution}"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
