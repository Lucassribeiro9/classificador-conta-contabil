from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath


_HEADER = "## Homologacao manual"
_FIELD_BY_LABEL = {
    "Resultado": "result",
    "Commit testado": "commit_tested",
    "Ambiente": "environment",
    "Perfil": "profile",
    "Roteiro executado": "runbook",
    "Evidencias": "evidence",
    "Divergencias": "divergences",
}
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_RESULTS = {"APROVADO", "REPROVADO", "BLOQUEADO", "NAO APLICAVEL"}


@dataclass(frozen=True)
class ManualHomologationComment:
    result: str
    commit_tested: str
    environment: str
    profile: str
    runbook: str
    evidence: tuple[str, ...]
    divergences: tuple[str, ...]
    comment_id: int
    author: str
    location: str
    edited: bool
    issue_number: int
    pull_request_number: int


@dataclass(frozen=True)
class RelevantTreeSnapshot:
    commit_sha: str
    blobs_by_path: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not _SHA_PATTERN.fullmatch(self.commit_sha):
            raise ValueError("commit_sha must be a full lowercase SHA.")
        paths: list[str] = []
        for path, blob_sha in self.blobs_by_path:
            normalized = PurePosixPath(path)
            if (
                normalized.is_absolute()
                or ".." in normalized.parts
                or normalized.as_posix() != path
                or not _SHA_PATTERN.fullmatch(blob_sha)
            ):
                raise ValueError("Relevant tree contains an unsafe path or blob SHA.")
            paths.append(path)
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("Relevant tree paths must be unique and sorted.")

    def digest(self) -> str:
        canonical = "".join(
            f"{path}\0{blob_sha}\0" for path, blob_sha in self.blobs_by_path
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HomologationContext:
    expected_issue_number: int
    expected_pull_request_number: int
    expected_author: str
    expected_location: str
    tested_tree: RelevantTreeSnapshot
    current_tree: RelevantTreeSnapshot


@dataclass(frozen=True)
class HomologationDecision:
    accepted: bool
    target_state: str
    code: str
    sanitized_reason: str


def parse_manual_homologation_comment(
    body: str,
    *,
    comment_id: int,
    author: str,
    location: str,
    edited: bool,
    issue_number: int,
    pull_request_number: int,
) -> ManualHomologationComment | None:
    if (
        comment_id < 1
        or author != "Lucassribeiro9"
        or location != "expected_draft_pr"
        or edited
        or not body.splitlines()
        or body.splitlines()[0] != _HEADER
    ):
        return None

    values: dict[str, str] = {}
    for raw_line in body.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("- ") or ": " not in line:
            return None
        label, value = line[2:].split(": ", 1)
        field = _FIELD_BY_LABEL.get(label)
        if field is None or field in values or not value.strip():
            return None
        values[field] = value.strip()

    if set(values) != set(_FIELD_BY_LABEL.values()):
        return None
    if values["result"] not in _ALLOWED_RESULTS:
        return None
    if not _SHA_PATTERN.fullmatch(values["commit_tested"]):
        return None

    evidence = _split_items(values["evidence"])
    divergences = _split_items(values["divergences"])
    if not evidence or not divergences:
        return None

    return ManualHomologationComment(
        result=values["result"],
        commit_tested=values["commit_tested"],
        environment=values["environment"],
        profile=values["profile"],
        runbook=values["runbook"],
        evidence=evidence,
        divergences=divergences,
        comment_id=comment_id,
        author=author,
        location=location,
        edited=edited,
        issue_number=issue_number,
        pull_request_number=pull_request_number,
    )


def evaluate_homologation(
    comment: ManualHomologationComment | None,
    context: HomologationContext,
) -> HomologationDecision:
    if comment is None:
        return _rejected("MANUAL_HOMOLOGATION_MISSING", "Manual homologation is missing.")
    if (
        comment.issue_number != context.expected_issue_number
        or comment.pull_request_number != context.expected_pull_request_number
        or comment.author != context.expected_author
        or comment.location != context.expected_location
    ):
        return _rejected("HOMOLOGATION_CONTEXT_MISMATCH", "Homologation context is invalid.")
    if comment.result != "APROVADO":
        target_state = (
            "agent:blocked"
            if comment.result in {"REPROVADO", "BLOQUEADO"}
            else "agent:awaiting-manual-test"
        )
        return _rejected(
            "MANUAL_HOMOLOGATION_NOT_APPROVED",
            "Manual homologation was not approved.",
            target_state=target_state,
        )
    if comment.commit_tested != context.tested_tree.commit_sha:
        return _rejected("COMMIT_MISMATCH", "Tested commit does not match the evidence.")
    if context.tested_tree.digest() != context.current_tree.digest():
        return _rejected("RELEVANT_TREE_CHANGED", "Relevant content changed.")
    return HomologationDecision(
        accepted=True,
        target_state="agent:validated",
        code="MANUAL_HOMOLOGATION_ACCEPTED",
        sanitized_reason="Manual homologation accepted.",
    )


def _split_items(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def _rejected(
    code: str,
    sanitized_reason: str,
    *,
    target_state: str = "agent:awaiting-manual-test",
) -> HomologationDecision:
    return HomologationDecision(
        accepted=False,
        target_state=target_state,
        code=code,
        sanitized_reason=sanitized_reason,
    )
