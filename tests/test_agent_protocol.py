import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".github/agent-protocol.json"
SCHEMA_PATH = ROOT / ".github/agent-protocol.schema.json"
DOC_PATH = ROOT / "docs/agent-protocol.md"

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def test_agent_protocol_manifest_satisfies_its_json_schema():
    schema = _load_json(SCHEMA_PATH)
    manifest = _load_json(MANIFEST_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)

def test_agent_protocol_defines_exactly_the_approved_operational_labels():
    manifest = _load_json(MANIFEST_PATH)

    assert manifest["eligibility_label"] == "ready-for-agent"
    assert manifest["no_operational_state"] is None
    assert manifest["operational_labels"] == [
        {
            "name": "agent:awaiting-task-review",
            "color": "C5DEF5",
            "description": "Task Review ainda não concluída ou invalidada.",
        },
        {
            "name": "agent:awaiting-human",
            "color": "FBCA04",
            "description": "Existe decisão, pergunta ou autorização humana pendente.",
        },
        {
            "name": "agent:ready-to-implement",
            "color": "0E8A16",
            "description": "Task Review aprovada e implementação autorizada.",
        },
        {
            "name": "agent:running",
            "color": "5319E7",
            "description": "Runner mantém a trava e está executando a issue.",
        },
        {
            "name": "agent:awaiting-manual-test",
            "color": "F9D0C4",
            "description": "Draft e roteiro aguardam homologação manual.",
        },
        {
            "name": "agent:validated",
            "color": "006B75",
            "description": "Conteúdo do commit atual foi homologado.",
        },
        {
            "name": "agent:blocked",
            "color": "B60205",
            "description": "Execução requer intervenção antes de continuar.",
        },
        {
            "name": "agent:cancelled",
            "color": "6A737D",
            "description": "Execução cancelada pelo mantenedor.",
        },
    ]

def test_agent_protocol_has_complete_unambiguous_state_machine():
    manifest = _load_json(MANIFEST_PATH)
    transitions = manifest["transitions"]
    known_states = {item["name"] for item in manifest["operational_labels"]} | {None}

    assert all(item["from_state"] in known_states for item in transitions)
    assert all(item["to_state"] in known_states for item in transitions)

    transition_keys = [(item["from_state"], item["event"]) for item in transitions]
    assert len(transition_keys) == len(set(transition_keys))

    expected_spec_transitions = {
        (None, "task_review_started", "agent:awaiting-task-review", "orchestrator"),
        ("agent:awaiting-task-review", "blocking_question_raised", "agent:awaiting-human", "agent"),
        ("agent:awaiting-human", "decision_recorded", "agent:awaiting-task-review", "orchestrator"),
        ("agent:awaiting-task-review", "task_review_approved", "agent:ready-to-implement", "maintainer"),
        ("agent:ready-to-implement", "implementation_started", "agent:running", "runner"),
        ("agent:running", "new_decision_required", "agent:awaiting-human", "runner"),
        ("agent:running", "draft_ready", "agent:awaiting-manual-test", "runner"),
        ("agent:running", "automatic_correction_exhausted", "agent:blocked", "runner"),
        ("agent:running", "execution_timed_out", "agent:blocked", "runner"),
        ("agent:running", "cancellation_completed", "agent:cancelled", "runner"),
        ("agent:blocked", "retry_completed", "agent:running", "runner"),
        ("agent:cancelled", "task_review_reapproved", "agent:ready-to-implement", "maintainer"),
        ("agent:awaiting-manual-test", "manual_test_approved", "agent:validated", "orchestrator"),
        ("agent:awaiting-manual-test", "manual_test_rejected_or_blocked", "agent:blocked", "orchestrator"),
        ("agent:validated", "validated_content_changed", "agent:awaiting-manual-test", "orchestrator"),
        ("agent:validated", "issue_closed", None, "orchestrator"),
    }
    actual_transitions = {
        (item["from_state"], item["event"], item["to_state"], item["responsible"])
        for item in transitions
    }
    assert expected_spec_transitions <= actual_transitions

    closed_sources = {
        item["from_state"] for item in transitions if item["event"] == "issue_closed"
    }
    assert closed_sources == known_states - {None}

def test_human_intervention_contract_is_strict_auditable_and_pending_when_async():
    manifest = _load_json(MANIFEST_PATH)
    interventions = manifest["human_interventions"]
    commands = {item["name"]: item for item in interventions["commands"]}

    assert interventions["authorized_actors"] == ["Lucassribeiro9"]
    assert interventions["accepted_source"] == {
        "event": "issue_comment.created",
        "location": "issue",
        "edited_comments_authorize": False,
    }
    assert interventions["manual_homologation_location"] == "expected_draft_pr"
    assert interventions["unauthorized_events"] == {
        "public_response": False,
        "state_change": False,
        "future_private_audit": True,
    }
    assert set(commands) == {"approve-task-review", "decide", "retry", "cancel"}

    decide_pattern = re.compile(commands["decide"]["first_line_pattern"])
    for accepted in ("/agent decide A", "/agent decide a", "/agent decide B", "/agent decide opcao-a"):
        assert decide_pattern.fullmatch(accepted)
    for rejected in (
        "/Agent decide A",
        " /agent decide A",
        "/agent  decide A",
        "/agent decide A ",
        "/agent decide A porque sim",
    ):
        assert decide_pattern.fullmatch(rejected) is None

    assert commands["decide"]["normalization"] == {
        "type": "option_token",
        "canonical_format": "opcao-{slug}",
        "case_insensitive": True,
        "examples": {
            "A": "opcao-a",
            "a": "opcao-a",
            "opcao-a": "opcao-a",
        },
    }
    assert commands["decide"]["option_must_be_offered"] is True
    assert commands["decide"]["requires_single_pending_question"] is True
    assert commands["decide"]["rejection_if_option_not_offered"] == "invalid_option"
    assert commands["decide"]["rejection_if_no_pending_question"] == "no_pending_decision"

    assert commands["approve-task-review"]["required_task_review_result"] == "PRONTA PARA APROVACAO"
    assert set(commands["approve-task-review"]["required_context_evidence"]) >= {
        "issue_body_sha256",
        "task_review_comment_id",
        "task_review_body_sha256",
        "spec_path",
        "spec_commit_sha",
        "approved_branch",
    }
    assert commands["approve-task-review"]["rejection_if_incomplete"] == "task_review_incomplete"

    assert commands["retry"]["initial_result"] == "accepted_pending"
    assert commands["retry"]["changes_state_on_acceptance"] is False
    assert commands["cancel"]["initial_result"] == "accepted_pending"
    assert commands["cancel"]["changes_state_on_acceptance"] is False

def test_state_policies_reject_invalid_or_conflicting_state_without_mutation():
    manifest = _load_json(MANIFEST_PATH)
    policies = manifest["state_policies"]

    assert policies["operational_label_prefix"] == "agent:"
    assert policies["operational_state_is_exclusive"] is True
    assert policies["preserve_non_operational_labels"] is True
    assert policies["release_1_blocking"] is False
    assert policies["invalid_transition"] == {
        "result": "rejected",
        "code": "transition_not_allowed",
        "preserve_state": True,
        "preserve_labels": True,
    }
    assert policies["multiple_operational_labels"] == {
        "result": "rejected",
        "code": "state_conflict",
        "automatic_repair": False,
        "preserve_labels": True,
        "requires_human_correction": True,
    }
    assert policies["native_issue_lifecycle"] == {
        "closed_is_executable": False,
        "interrupt_active_execution": True,
        "preserve_evidence": True,
        "remove_operational_label": True,
        "reopened_operational_state": None,
        "reopened_requires_new_task_review": True,
    }

    assert set(manifest["rejection_codes"]) >= {
        "transition_not_allowed",
        "wrong_location",
        "no_pending_decision",
        "invalid_option",
        "task_review_incomplete",
        "state_conflict",
        "wrong_author",
        "wrong_event",
    }

def test_structured_confirmation_schema_accepts_public_evidence_and_rejects_extra_fields():
    schema = _load_json(SCHEMA_PATH)
    manifest = _load_json(MANIFEST_PATH)
    confirmation_contract = manifest["structured_confirmations"]
    confirmation_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": confirmation_contract["schema_ref"],
        "$defs": schema["$defs"],
    }
    validator = Draft202012Validator(confirmation_schema, format_checker=FormatChecker())

    accepted = {
        "schema_version": "1.0.0",
        "confirmation_id": "agent-confirmation-example-1",
        "result": "accepted",
        "command": {
            "original": "/agent decide A",
            "normalized": "/agent decide opcao-a",
        },
        "actor": "Lucassribeiro9",
        "occurred_at": "2026-07-29T20:00:00Z",
        "repository": "Lucassribeiro9/classificador-conta-contabil",
        "issue_number": 372,
        "source_comment": {
            "id": 123456,
            "url": "https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/372#issuecomment-123456",
            "created_at": "2026-07-29T19:59:00Z",
            "edited": False,
        },
        "previous_state": "agent:awaiting-human",
        "new_state": "agent:awaiting-task-review",
        "execution_id": None,
        "context_validation": {
            "author": "passed",
            "event": "passed",
            "location": "passed",
            "command": "passed",
            "state": "passed",
            "task_review": "not_applicable",
        },
        "rejection_code": None,
        "approval_context": None,
    }
    validator.validate(accepted)

    rejected = {
        **accepted,
        "confirmation_id": "agent-confirmation-example-2",
        "result": "rejected",
        "new_state": "agent:awaiting-human",
        "rejection_code": "invalid_option",
    }
    validator.validate(rejected)

    with pytest.raises(ValidationError):
        validator.validate({**accepted, "token": "must-not-be-accepted"})

    assert confirmation_contract["format"] == "markdown_summary_with_json"
    assert set(confirmation_contract["forbidden_fields"]) >= {
        "token",
        "secret",
        "prompt",
        "private_metrics",
        "accounting_data",
    }

def test_agent_protocol_documentation_explains_operation_without_claiming_runtime_automation():
    documentation = DOC_PATH.read_text(encoding="utf-8")

    for required_text in (
        "docs/specs/14-esteira-agentes-supervisionada.md",
        ".github/agent-protocol.json",
        ".github/agent-protocol.schema.json",
        "ready-for-agent",
        "open/closed",
        "agent:awaiting-task-review",
        "agent:awaiting-human",
        "agent:ready-to-implement",
        "agent:running",
        "agent:awaiting-manual-test",
        "agent:validated",
        "agent:blocked",
        "agent:cancelled",
        "/agent approve-task-review",
        "/agent decide A",
        "/agent retry",
        "/agent cancel",
        "uma pergunta por vez",
        "draft PR esperado",
        "não implementa o runner",
        "não bloqueia a Release 1",
    ):
        assert required_text in documentation

def test_task_review_approval_context_is_hash_bound_and_schema_validated():
    schema = _load_json(SCHEMA_PATH)
    manifest = _load_json(MANIFEST_PATH)
    contract = manifest["task_review_approval"]
    approval_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": contract["schema_ref"],
        "$defs": schema["$defs"],
    }
    validator = Draft202012Validator(approval_schema, format_checker=FormatChecker())
    approval = {
        "task_review_result": "PRONTA PARA APROVACAO",
        "has_pending_question": False,
        "has_blocking_contradiction": False,
        "issue_body_sha256": "a" * 64,
        "task_review_comment_id": 123456,
        "task_review_body_sha256": "b" * 64,
        "spec_path": "docs/specs/14-esteira-agentes-supervisionada.md",
        "spec_commit_sha": "c" * 40,
        "approved_branch": "chore/agent-protocolo-github",
        "approved_by": "Lucassribeiro9",
        "approved_at": "2026-07-29T20:00:00Z",
    }

    validator.validate(approval)
    validator.validate({**approval, "spec_path": None, "spec_commit_sha": None})
    with pytest.raises(ValidationError):
        validator.validate({**approval, "issue_body_sha256": "not-a-sha256"})

    assert contract["context_change_invalidates_approval"] is True
    assert contract["cancelled_reapproval_reuses_context_only_when_unchanged"] is True
