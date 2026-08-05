import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / ".agents/contracts/delivery-skill-output.schema.json"
ROUTING_PATH = ROOT / ".agents/contracts/issue-delivery-loop-routing.json"
PROMPT_GUIDE_PATH = ROOT / "docs/prompts-fluxo-sdd-tdd.md"
FIXTURES_PATH = ROOT / "tests/fixtures/agent_skills"
SKILLS_PATH = ROOT / ".agents/skills"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_skill(name: str) -> tuple[dict, str]:
    content = (SKILLS_PATH / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", content, flags=re.DOTALL)

    assert match is not None
    return yaml.safe_load(match.group(1)), match.group(2)



def test_task_review_output_satisfies_the_shared_contract():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(FIXTURES_PATH / "task-review-documental-ready.json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(output)


def test_task_review_v2_requires_an_explicit_delivery_track():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(FIXTURES_PATH / "task-review-documental-ready.json")
    validator = Draft202012Validator(schema)

    assert schema["properties"]["contract_version"]["const"] == "2.0.0"
    assert output["contract_version"] == "2.0.0"
    assert output["payload"]["delivery_track"] == "implementation"
    validator.validate(output)

    without_delivery_track = {
        **output,
        "payload": {
            key: value
            for key, value in output["payload"].items()
            if key != "delivery_track"
        },
    }
    with pytest.raises(ValidationError):
        validator.validate(without_delivery_track)


def test_coordinator_routes_pending_task_review_without_copying_its_procedure():
    routing = _load_json(ROUTING_PATH)
    metadata, instructions = _load_skill("issue-delivery-loop")

    route = next(
        route
        for route in routing["routes"]
        if route["stage"] == "task_review" and route["status"] == "pending"
    )

    assert routing["routing_version"] == "1.0.0"
    assert routing["output_contract_version"] == "2.0.0"
    assert route["selected_skill"] == "issue-task-review"
    assert route["delivery_track"] is None
    assert metadata["name"] == "issue-delivery-loop"
    assert ".agents/contracts/issue-delivery-loop-routing.json" in instructions
    assert ".agents/skills/issue-task-review/SKILL.md" in instructions
    assert "carregue a skill selecionada" in instructions
    assert "uma pergunta por vez" not in instructions
    assert "## Procedimento" not in instructions


def test_coordinator_routes_delivery_by_explicit_delivery_track():
    routes = _load_json(ROUTING_PATH)["routes"]

    spec_route = next(
        route
        for route in routes
        if route["stage"] == "delivery"
        and route["status"] == "pending"
        and route["delivery_track"] == "spec"
    )
    implementation_route = next(
        route
        for route in routes
        if route["stage"] == "delivery"
        and route["status"] == "pending"
        and route["delivery_track"] == "implementation"
    )

    assert spec_route["selected_skill"] == "spec-delivery"
    assert implementation_route["selected_skill"] == "implement-issue"
    for route in (spec_route, implementation_route):
        assert route["required_previous_skill"] == "issue-task-review"
        assert route["required_previous_outcomes"] == ["ready_for_approval"]
        assert route["github_states"] == [
            "agent:ready-to-implement",
            "agent:running",
        ]


def test_coordinator_routes_each_completed_delivery_track_to_draft():
    routes = _load_json(ROUTING_PATH)["routes"]
    expected_previous_skills = {
        "spec": "spec-delivery",
        "implementation": "implement-issue",
    }

    for delivery_track, previous_skill in expected_previous_skills.items():
        route = next(
            route
            for route in routes
            if route["stage"] == "draft"
            and route["status"] == "pending"
            and route["delivery_track"] == delivery_track
        )

        assert route["github_states"] == ["agent:running"]
        assert route["selected_skill"] == "prepare-draft-pr"
        assert (
            route["selected_skill_source"]
            == ".agents/skills/prepare-draft-pr/SKILL.md"
        )
        assert route["required_previous_skill"] == previous_skill
        assert route["required_previous_outcomes"] == ["completed"]


def test_coordinator_stops_at_manual_homologation_without_selecting_a_skill():
    routes = _load_json(ROUTING_PATH)["routes"]
    route = next(
        route
        for route in routes
        if route["stage"] == "manual_homologation"
        and route["status"] == "pending"
    )

    assert route["mode"] == "human_gate"
    assert route["github_states"] == ["agent:awaiting-manual-test"]
    assert route["selected_skill"] is None
    assert route["selected_skill_source"] is None
    assert route["required_previous_skill"] == "prepare-draft-pr"
    assert route["required_previous_outcomes"] == ["draft_created"]
    assert route["prompt_section"] == "manual-homologation"


def test_coordinator_handoff_output_satisfies_the_v2_contract():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(
        FIXTURES_PATH / "issue-delivery-loop-delivery-ready.json"
    )
    validator = Draft202012Validator(schema)

    validator.validate(output)
    assert output["skill"] == "issue-delivery-loop"
    assert output["outcome"] == "delegation_ready"
    assert output["payload"]["delegation_allowed"] is True
    assert output["payload"]["selected_skill"] == "implement-issue"
    assert output["payload"]["checkpoint"] == {
        "stage": "delivery",
        "status": "pending",
        "attempt": 1,
        "previous_output_ref": "issue-comment:12345",
        "idempotency_key": f"sha256:{'a' * 64}",
    }
    assert output["payload"]["fallback"]["comment_location"] == "issue"
    assert output["payload"]["fallback"]["append_only"] is True

    with pytest.raises(ValidationError):
        validator.validate({**output, "prompt": "forbidden"})


@pytest.mark.parametrize(
    ("filename", "reason_code"),
    [
        ("issue-delivery-loop-unknown-state-blocked.json", "unknown_state"),
        (
            "issue-delivery-loop-invalid-previous-output-blocked.json",
            "invalid_previous_output",
        ),
    ],
)
def test_coordinator_fails_closed_for_invalid_state_or_previous_output(
    filename,
    reason_code,
):
    validator = Draft202012Validator(_load_json(SCHEMA_PATH))
    output = _load_json(FIXTURES_PATH / filename)

    validator.validate(output)
    assert output["skill"] == "issue-delivery-loop"
    assert output["outcome"] == "blocked"
    assert output["requires_human"] is True
    assert output["payload"]["delegation_allowed"] is False
    assert output["payload"]["selected_skill"] is None
    assert output["payload"]["checkpoint"]["status"] == "blocked"
    assert output["blocking_reasons"][0]["code"] == reason_code


def test_coordinator_manifest_forbids_automatic_retry_and_next_issue_start():
    routing = _load_json(ROUTING_PATH)
    _, instructions = _load_skill("issue-delivery-loop")

    assert routing["idempotency"] == {
        "algorithm": "sha256",
        "components": [
            "repository",
            "issue_number",
            "stage",
            "attempt",
            "previous_output_ref",
        ],
        "duplicate_result": "reuse_without_delegation",
    }
    assert routing["retry_policy"] == {
        "requires_human_event": "retry_completed",
        "automatic_retry": False,
    }
    assert routing["checkpoint_policy"]["append_only"] is True
    assert routing["checkpoint_policy"]["edited_comment_is_valid"] is False
    assert routing["next_issue_policy"] == {
        "source": "ordered_parent_sub_issues",
        "requirements": [
            "open",
            "eligible",
            "dependencies_resolved",
        ],
        "action": "suggest_only",
        "on_ambiguity": None,
    }
    assert routing["blocked_states"] == ["agent:blocked", "agent:cancelled"]
    assert "Nunca inicie a próxima issue" in instructions
    assert "Nunca faça retry sem intervenção humana válida" in instructions


def test_manual_fallback_maps_every_route_to_a_sanitized_human_prompt():
    routing = _load_json(ROUTING_PATH)
    guide = PROMPT_GUIDE_PATH.read_text(encoding="utf-8")
    fallback = (
        ROOT / ".agents/references/issue-delivery-loop-fallback.md"
    ).read_text(encoding="utf-8")

    prompt_sections = {route["prompt_section"] for route in routing["routes"]}
    assert prompt_sections == {
        "task-review",
        "spec-delivery",
        "implementation",
        "draft-pr",
        "manual-homologation",
    }
    for section in prompt_sections:
        assert f"`prompt_section: {section}`" in guide
        assert f"| `{section}` |" in fallback

    for skill_name in (
        "issue-task-review",
        "spec-delivery",
        "implement-issue",
        "prepare-draft-pr",
    ):
        assert skill_name in guide

    assert "comentário novo e append-only" in fallback
    assert "prompts completos" in fallback
    assert "métricas de tokens" in fallback


def test_spec_delivery_output_satisfies_the_shared_contract():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(FIXTURES_PATH / "spec-delivery-documental-completed.json")

    Draft202012Validator(schema).validate(output)


def test_implement_issue_output_satisfies_the_shared_contract():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(FIXTURES_PATH / "implement-configuracao-testavel-completed.json")

    Draft202012Validator(schema).validate(output)


def test_prepare_draft_pr_output_satisfies_the_shared_contract():
    schema = _load_json(SCHEMA_PATH)
    output = _load_json(FIXTURES_PATH / "prepare-draft-pr-created.json")

    Draft202012Validator(schema).validate(output)


def test_issue_task_review_has_a_bounded_structured_procedure():
    metadata, instructions = _load_skill("issue-task-review")

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "issue-task-review"
    assert not (SKILLS_PATH / "issue-task-review/agents/openai.yaml").exists()

    for required_text in (
        ".agents/contracts/delivery-skill-output.schema.json",
        ".agents/references/delivery-skill-sources.md",
        "Contexto obrigatório",
        "Contexto condicional",
        "Contexto proibido",
        "uma pergunta por vez",
        "PRONTA PARA APROVACAO",
        "BLOQUEADA",
        "REQUER SPEC",
        "REQUER REESCOPAGEM",
        "Nunca implemente",
        "Nunca altere labels ou estados",
        "Não avance para outra issue",
    ):
        assert required_text in instructions


def test_spec_delivery_has_a_bounded_structured_procedure():
    metadata, instructions = _load_skill("spec-delivery")

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "spec-delivery"
    assert not (SKILLS_PATH / "spec-delivery/agents/openai.yaml").exists()

    for required_text in (
        ".agents/contracts/delivery-skill-output.schema.json",
        ".agents/references/delivery-skill-sources.md",
        "Contexto obrigatório",
        "Contexto condicional",
        "Contexto proibido",
        "Edite somente a spec autorizada",
        "PRD para visão de produto",
        "spec para contrato técnico",
        "issue para unidade de trabalho",
        "Não gere issues",
        "Não implemente código",
        "Não avance para outra issue",
    ):
        assert required_text in instructions


def test_implement_issue_has_conditional_tdd_and_public_seam_guards():
    metadata, instructions = _load_skill("implement-issue")

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "implement-issue"
    assert not (SKILLS_PATH / "implement-issue/agents/openai.yaml").exists()

    for required_text in (
        ".agents/contracts/delivery-skill-output.schema.json",
        ".agents/references/delivery-skill-sources.md",
        "Contexto obrigatório",
        "Contexto condicional",
        "Contexto proibido",
        "uma única issue",
        "documental",
        "comportamental",
        "configuracao-testavel",
        "mista",
        "TDD artificial",
        "RED → GREEN",
        "seam público",
        "Preserve alterações preexistentes",
        "Não faça commit, push ou draft PR",
        "Não avance para outra issue",
    ):
        assert required_text in instructions


def test_prepare_draft_pr_requires_real_evidence_and_stops_at_draft():
    metadata, instructions = _load_skill("prepare-draft-pr")

    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "prepare-draft-pr"
    assert not (SKILLS_PATH / "prepare-draft-pr/agents/openai.yaml").exists()

    for required_text in (
        ".agents/contracts/delivery-skill-output.schema.json",
        ".agents/references/delivery-skill-sources.md",
        ".github/pull_request_template.md",
        "Contexto obrigatório",
        "Contexto condicional",
        "Contexto proibido",
        "evidências reais",
        "arquivo inesperado",
        "teste obrigatório falhando",
        "commit focado",
        "branch aprovada",
        "draft PR",
        "roteiro manual reproduzível",
        "Nunca marque o PR como ready",
        "Nunca faça merge",
        "Nunca feche a issue",
        "Não avance para outra issue",
    ):
        assert required_text in instructions


def test_sanitized_fixtures_cover_all_issue_classifications():
    classifications = {
        fixture["classification"]
        for path in FIXTURES_PATH.glob("*.json")
        if (fixture := _load_json(path))
    }

    assert classifications == {
        "documental",
        "comportamental",
        "configuracao-testavel",
        "mista",
    }


def test_sanitized_fixtures_cover_approved_blocking_scenarios():
    expected = {
        "task-review-contradiction-blocked.json",
        "task-review-missing-dependency-blocked.json",
        "spec-delivery-new-decision-blocked.json",
        "implement-scope-expansion-blocked.json",
        "prepare-draft-insufficient-evidence-blocked.json",
        "prepare-draft-unexpected-file-blocked.json",
        "implement-mandatory-test-failing-blocked.json",
        "implement-next-issue-attempt-blocked.json",
    }
    available = {path.name for path in FIXTURES_PATH.glob("*.json")}

    assert expected <= available

    validator = Draft202012Validator(_load_json(SCHEMA_PATH))
    for filename in expected:
        output = _load_json(FIXTURES_PATH / filename)
        validator.validate(output)
        assert output["outcome"] == "blocked"
        assert output["requires_human"] is True
        assert output["blocking_reasons"]


def test_shared_contract_rejects_extra_fields_and_incomplete_created_drafts():
    validator = Draft202012Validator(_load_json(SCHEMA_PATH))

    task_review = _load_json(FIXTURES_PATH / "task-review-documental-ready.json")
    with pytest.raises(ValidationError):
        validator.validate({**task_review, "token": "forbidden"})

    mismatched_payload = {
        **task_review,
        "skill": "spec-delivery",
        "outcome": "completed",
    }
    with pytest.raises(ValidationError):
        validator.validate(mismatched_payload)

    created_draft = _load_json(FIXTURES_PATH / "prepare-draft-pr-created.json")
    created_without_pr = {
        **created_draft,
        "payload": {**created_draft["payload"], "pull_request": None},
    }
    with pytest.raises(ValidationError):
        validator.validate(created_without_pr)

    created_without_event = {**created_draft, "recommended_event": None}
    with pytest.raises(ValidationError):
        validator.validate(created_without_event)

    created_with_non_ascii_title = {
        **created_draft,
        "payload": {
            **created_draft["payload"],
            "title": "feat(agent): alteração sanitizada",
        },
    }
    with pytest.raises(ValidationError):
        validator.validate(created_with_non_ascii_title)


def test_agent_catalog_lists_delivery_skills_and_their_shared_contract():
    catalog = (ROOT / ".agents/README.md").read_text(encoding="utf-8")

    for required_text in (
        "issue-task-review",
        "spec-delivery",
        "implement-issue",
        "prepare-draft-pr",
        ".agents/contracts/delivery-skill-output.schema.json",
        ".agents/references/delivery-skill-sources.md",
        "não coordenam a esteira",
    ):
        assert required_text in catalog

    assert "agents/openai.yaml" not in catalog


def test_documental_implementation_does_not_invent_tdd_cycles():
    output = _load_json(FIXTURES_PATH / "implement-documental-completed.json")

    Draft202012Validator(_load_json(SCHEMA_PATH)).validate(output)
    assert output["skill"] == "implement-issue"
    assert output["classification"] == "documental"
    assert output["outcome"] == "completed"
    assert output["payload"]["process_type"] == "documental"
    assert output["payload"]["tdd_applied"] is False
    assert output["payload"]["red_green_cycles"] == []
    assert output["payload"]["validations"] == [
        "git diff --check",
        "Inspeção integral do diff",
    ]


def test_implement_contract_enforces_classification_specific_tdd():
    validator = Draft202012Validator(_load_json(SCHEMA_PATH))
    documental = _load_json(FIXTURES_PATH / "implement-documental-completed.json")
    configuracao = _load_json(
        FIXTURES_PATH / "implement-configuracao-testavel-completed.json"
    )

    documental_with_artificial_tdd = {
        **documental,
        "payload": {
            **documental["payload"],
            "tdd_applied": True,
        },
    }
    with pytest.raises(ValidationError):
        validator.validate(documental_with_artificial_tdd)

    behavior_without_tdd = {
        **configuracao,
        "classification": "comportamental",
        "payload": {
            **configuracao["payload"],
            "process_type": "comportamental",
            "tdd_applied": False,
            "red_green_cycles": [],
        },
    }
    with pytest.raises(ValidationError):
        validator.validate(behavior_without_tdd)

    mismatched_classification = {
        **configuracao,
        "payload": {**configuracao["payload"], "process_type": "documental"},
    }
    with pytest.raises(ValidationError):
        validator.validate(mismatched_classification)

def test_every_fixture_is_valid_and_recommends_only_protocol_events():
    validator = Draft202012Validator(_load_json(SCHEMA_PATH))
    protocol = _load_json(ROOT / ".github/agent-protocol.json")
    protocol_events = {transition["event"] for transition in protocol["transitions"]}

    for path in FIXTURES_PATH.glob("*.json"):
        output = _load_json(path)
        validator.validate(output)
        if output["recommended_event"] is not None:
            assert output["recommended_event"] in protocol_events


def test_delivery_skills_declare_on_demand_context_without_copying_prompt_guide():
    source_matrix = (
        ROOT / ".agents/references/delivery-skill-sources.md"
    ).read_text(encoding="utf-8")

    for skill_name in (
        "issue-task-review",
        "spec-delivery",
        "implement-issue",
        "prepare-draft-pr",
    ):
        _, instructions = _load_skill(skill_name)

        assert f"| `{skill_name}` |" in source_matrix
        assert instructions.count("### Contexto obrigatório") == 1
        assert instructions.count("### Contexto condicional") == 1
        assert instructions.count("### Contexto proibido") == 1
        assert ".agents/references/delivery-skill-sources.md" in instructions
        assert "docs/prompts-fluxo-sdd-tdd.md" in instructions
        assert "## Prompt Para" not in instructions
        assert len(instructions.splitlines()) < 100
