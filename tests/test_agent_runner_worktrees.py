import subprocess
from pathlib import Path

from agent_runner.git_workspace import (
    DraftPullRequestRequest,
    GitWorkspaceManager,
    GitWorkspaceRequest,
)


class FakeDraftPublisher:
    def __init__(self) -> None:
        self.requests: list[DraftPullRequestRequest] = []

    def create_draft(self, request: DraftPullRequestRequest) -> str:
        self.requests.append(request)
        return "draft://pr/1"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


def _init_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    _git(origin, "config", "user.name", "Test User")
    _git(origin, "config", "user.email", "test@example.invalid")
    (origin / "allowed.txt").write_text("base\n", encoding="utf-8")
    _git(origin, "add", "allowed.txt")
    _git(origin, "commit", "-m", "base")
    base_sha = _git(origin, "rev-parse", "HEAD")

    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(origin, "remote", "add", "origin", str(remote))
    _git(origin, "push", "-u", "origin", "main")
    return origin, remote, base_sha


def test_prepare_publishes_allowed_commit_from_isolated_worktree(tmp_path: Path):
    repository, remote, base_sha = _init_repo(tmp_path)
    publisher = FakeDraftPublisher()
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=publisher,
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_1234567890abcdef",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
            mutate=lambda worktree: (worktree / "allowed.txt").write_text(
                "base\nchange\n",
                encoding="utf-8",
            ),
        )
    )

    assert result.error_code is None
    assert result.branch == "feat/agent-runner-worktrees"
    assert result.base_sha == base_sha
    assert result.commit_sha is not None
    assert result.pushed is True
    assert result.draft_requested is True
    assert result.changed_files == ["allowed.txt"]
    assert result.worktree_ref == "issue-376-exec_123456"
    assert _git(repository, "ls-remote", remote.as_posix(), "feat/agent-runner-worktrees")
    assert publisher.requests == [
        DraftPullRequestRequest(
            issue_number=376,
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            title="feat(agent): isolar execucoes com branches e worktrees",
            body="Closes #376",
            commit_sha=result.commit_sha,
        )
    ]


def test_base_sha_mismatch_blocks_before_creating_worktree(tmp_path: Path):
    repository, _remote, _base_sha = _init_repo(tmp_path)
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_bad_base",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha="0" * 40,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
            mutate=lambda worktree: (worktree / "allowed.txt").write_text("change\n", encoding="utf-8"),
        )
    )

    assert result.error_code == "BASE_SHA_MISMATCH"
    assert result.pushed is False
    assert result.draft_requested is False
    assert not (tmp_path / "private-worktrees" / "issue-376-exec_bad_ba").exists()


def test_out_of_scope_changes_are_preserved_and_block_publication(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    publisher = FakeDraftPublisher()
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=publisher,
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_dirty_scope",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
            mutate=lambda worktree: (worktree / "outside.txt").write_text(
                "do not publish\n",
                encoding="utf-8",
            ),
        )
    )

    worktree = tmp_path / "private-worktrees" / "issue-376-exec_dirty_"
    assert result.error_code == "OUT_OF_SCOPE_CHANGES"
    assert result.changed_files == ["outside.txt"]
    assert result.pushed is False
    assert result.draft_requested is False
    assert publisher.requests == []
    assert (worktree / "outside.txt").read_text(encoding="utf-8") == "do not publish\n"


def test_invalid_allowed_path_is_rejected_before_git_effects(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_bad_path",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["../outside.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
        )
    )

    assert result.error_code == "PATH_NOT_ALLOWED"
    assert result.pushed is False
    assert result.draft_requested is False
    assert not (tmp_path / "private-worktrees" / "issue-376-exec_bad_pa").exists()


def test_existing_branch_with_out_of_scope_commit_is_incompatible(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    _git(repository, "switch", "-c", "feat/agent-runner-worktrees")
    (repository / "outside.txt").write_text("already here\n", encoding="utf-8")
    _git(repository, "add", "outside.txt")
    _git(repository, "commit", "-m", "outside scope")
    _git(repository, "switch", "main")
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_bad_branch",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
        )
    )

    assert result.error_code == "BRANCH_INCOMPATIBLE"
    assert result.pushed is False
    assert result.draft_requested is False


def test_push_failure_preserves_local_commit_and_skips_draft(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    publisher = FakeDraftPublisher()
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=publisher,
    )

    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_push_fail",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="missing-remote",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
            mutate=lambda worktree: (worktree / "allowed.txt").write_text(
                "base\nlocal commit preserved\n",
                encoding="utf-8",
            ),
        )
    )

    worktree = tmp_path / "private-worktrees" / result.worktree_ref
    assert result.error_code == "PUSH_FAILED"
    assert result.commit_sha is not None
    assert result.pushed is False
    assert result.draft_requested is False
    assert publisher.requests == []
    assert _git(worktree, "rev-parse", "HEAD") == result.commit_sha
    assert (worktree / "allowed.txt").read_text(encoding="utf-8") == "base\nlocal commit preserved\n"


def test_cleanup_removes_only_clean_execution_worktree_and_keeps_branch(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )
    request = GitWorkspaceRequest(
        issue_number=376,
        execution_id="exec_cleanup_ok",
        branch="feat/agent-runner-worktrees",
        base_branch="main",
        base_sha=base_sha,
        allowed_paths=["allowed.txt"],
        commit_message="feat(agent): isolar execucoes com worktrees",
        remote_name="origin",
        draft_title="feat(agent): isolar execucoes com branches e worktrees",
        draft_body="Closes #376",
    )
    result = manager.prepare_publish_and_request_draft(request)
    worktree = tmp_path / "private-worktrees" / result.worktree_ref
    assert worktree.exists()

    cleanup = manager.cleanup_execution(issue_number=376, execution_id="exec_cleanup_ok")

    assert cleanup.error_code is None
    assert not worktree.exists()
    assert _git(repository, "rev-parse", "--verify", "feat/agent-runner-worktrees")


def test_cleanup_refuses_dirty_worktree_and_preserves_files(tmp_path: Path):
    repository, _remote, base_sha = _init_repo(tmp_path)
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )
    result = manager.prepare_publish_and_request_draft(
        GitWorkspaceRequest(
            issue_number=376,
            execution_id="exec_cleanup_dirty",
            branch="feat/agent-runner-worktrees",
            base_branch="main",
            base_sha=base_sha,
            allowed_paths=["allowed.txt"],
            commit_message="feat(agent): isolar execucoes com worktrees",
            remote_name="origin",
            draft_title="feat(agent): isolar execucoes com branches e worktrees",
            draft_body="Closes #376",
        )
    )
    worktree = tmp_path / "private-worktrees" / result.worktree_ref
    (worktree / "dirty.txt").write_text("preserve me\n", encoding="utf-8")

    cleanup = manager.cleanup_execution(issue_number=376, execution_id="exec_cleanup_dirty")

    assert cleanup.error_code == "WORKTREE_DIRTY"
    assert worktree.exists()
    assert (worktree / "dirty.txt").read_text(encoding="utf-8") == "preserve me\n"

    assert cleanup.error_code == "WORKTREE_DIRTY"
    assert worktree.exists()
    assert (worktree / "dirty.txt").read_text(encoding="utf-8") == "preserve me\n"


def test_cleanup_is_idempotent_when_worktree_was_manually_removed(tmp_path: Path):
    repository, _remote, _base_sha = _init_repo(tmp_path)
    manager = GitWorkspaceManager(
        repository_path=repository,
        worktrees_root=tmp_path / "private-worktrees",
        draft_publisher=FakeDraftPublisher(),
    )

    cleanup = manager.cleanup_execution(issue_number=376, execution_id="exec_missing_worktree")

    assert cleanup.error_code is None
    assert cleanup.worktree_ref == "issue-376-exec_missin"
