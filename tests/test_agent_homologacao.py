import pytest

from agent_runner.homologacao import (
    HomologationContext,
    RelevantTreeSnapshot,
    evaluate_homologation,
    parse_manual_homologation_comment,
)


def test_parses_complete_structured_manual_homologation_comment():
    comment = parse_manual_homologation_comment(
        """## Homologacao manual

- Resultado: APROVADO
- Commit testado: 0123456789abcdef0123456789abcdef01234567
- Ambiente: desenvolvimento isolado
- Perfil: mantenedor
- Roteiro executado: docs/agent-protocol.md#homologacao
- Evidencias: testes focados aprovados; diff sanitizado
- Divergencias: nenhuma
""",
        comment_id=10,
        author="Lucassribeiro9",
        location="expected_draft_pr",
        edited=False,
        issue_number=521,
        pull_request_number=600,
    )

    assert comment is not None
    assert comment.result == "APROVADO"
    assert comment.commit_tested == "0123456789abcdef0123456789abcdef01234567"
    assert comment.evidence == ("testes focados aprovados", "diff sanitizado")
    assert comment.divergences == ("nenhuma",)
    assert comment.comment_id == 10


def test_relevant_tree_digest_ignores_commit_identity_but_detects_blob_change():
    tested = RelevantTreeSnapshot(
        commit_sha="a" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", "1" * 40),),
    )
    rebased = RelevantTreeSnapshot(
        commit_sha="b" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", "1" * 40),),
    )
    changed = RelevantTreeSnapshot(
        commit_sha="c" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", "2" * 40),),
    )

    assert tested.digest() == rebased.digest()
    assert tested.digest() != changed.digest()


@pytest.mark.parametrize("path", ["../outside.py", "/absolute.py"])
def test_relevant_tree_rejects_unsafe_paths(path: str):
    with pytest.raises(ValueError):
        RelevantTreeSnapshot(
            commit_sha="a" * 40,
            blobs_by_path=((path, "1" * 40),),
        )


def test_approves_only_a_structured_comment_bound_to_the_relevant_tree():
    tested_tree = RelevantTreeSnapshot(
        commit_sha="a" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", "1" * 40),),
    )
    comment = parse_manual_homologation_comment(
        _comment_body(commit_sha=tested_tree.commit_sha),
        comment_id=10,
        author="Lucassribeiro9",
        location="expected_draft_pr",
        edited=False,
        issue_number=521,
        pull_request_number=600,
    )

    decision = evaluate_homologation(
        comment,
        HomologationContext(
            expected_issue_number=521,
            expected_pull_request_number=600,
            expected_author="Lucassribeiro9",
            expected_location="expected_draft_pr",
            tested_tree=tested_tree,
            current_tree=tested_tree,
        ),
    )

    assert decision.accepted is True
    assert decision.target_state == "agent:validated"
    assert decision.code == "MANUAL_HOMOLOGATION_ACCEPTED"


@pytest.mark.parametrize(
    ("pull_request_number", "result", "current_blob", "expected_code", "expected_state"),
    [
        (601, "APROVADO", "1" * 40, "HOMOLOGATION_CONTEXT_MISMATCH", "agent:awaiting-manual-test"),
        (600, "REPROVADO", "1" * 40, "MANUAL_HOMOLOGATION_NOT_APPROVED", "agent:blocked"),
        (600, "BLOQUEADO", "1" * 40, "MANUAL_HOMOLOGATION_NOT_APPROVED", "agent:blocked"),
        (600, "NAO APLICAVEL", "1" * 40, "MANUAL_HOMOLOGATION_NOT_APPROVED", "agent:awaiting-manual-test"),
        (600, "APROVADO", "2" * 40, "RELEVANT_TREE_CHANGED", "agent:awaiting-manual-test"),
    ],
)
def test_rejects_wrong_context_unapproved_result_or_material_tree_change(
    pull_request_number: int,
    result: str,
    current_blob: str,
    expected_code: str,
    expected_state: str,
):
    tested_tree = RelevantTreeSnapshot(
        commit_sha="a" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", "1" * 40),),
    )
    comment = parse_manual_homologation_comment(
        _comment_body(commit_sha=tested_tree.commit_sha, result=result),
        comment_id=10,
        author="Lucassribeiro9",
        location="expected_draft_pr",
        edited=False,
        issue_number=521,
        pull_request_number=pull_request_number,
    )
    current_tree = RelevantTreeSnapshot(
        commit_sha="b" * 40,
        blobs_by_path=(("agent_runner/homologacao.py", current_blob),),
    )

    decision = evaluate_homologation(
        comment,
        HomologationContext(
            expected_issue_number=521,
            expected_pull_request_number=600,
            expected_author="Lucassribeiro9",
            expected_location="expected_draft_pr",
            tested_tree=tested_tree,
            current_tree=current_tree,
        ),
    )

    assert decision.accepted is False
    assert decision.target_state == expected_state
    assert decision.code == expected_code


def _comment_body(*, commit_sha: str, result: str = "APROVADO") -> str:
    return f"""## Homologacao manual

- Resultado: {result}
- Commit testado: {commit_sha}
- Ambiente: desenvolvimento isolado
- Perfil: mantenedor
- Roteiro executado: docs/agent-protocol.md#homologacao
- Evidencias: testes focados aprovados
- Divergencias: nenhuma
"""


@pytest.mark.parametrize(
    ("body", "author", "location", "edited"),
    [
        (_comment_body(commit_sha="a" * 40).replace("- Perfil: mantenedor\n", ""), "Lucassribeiro9", "expected_draft_pr", False),
        (_comment_body(commit_sha="a" * 40) + "- Campo extra: invalido\n", "Lucassribeiro9", "expected_draft_pr", False),
        (_comment_body(commit_sha="a" * 40).replace("## Homologacao manual", "## Homologacao manual alterada"), "Lucassribeiro9", "expected_draft_pr", False),
        (_comment_body(commit_sha="a" * 40), "other-user", "expected_draft_pr", False),
        (_comment_body(commit_sha="a" * 40), "Lucassribeiro9", "issue", False),
        (_comment_body(commit_sha="a" * 40), "Lucassribeiro9", "expected_draft_pr", True),
    ],
)
def test_rejects_incomplete_unknown_or_ineligible_comment_metadata(
    body: str,
    author: str,
    location: str,
    edited: bool,
):
    assert (
        parse_manual_homologation_comment(
            body,
            comment_id=10,
            author=author,
            location=location,
            edited=edited,
            issue_number=521,
            pull_request_number=600,
        )
        is None
    )
