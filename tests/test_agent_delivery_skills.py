import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / ".agents/contracts/delivery-skill-output.schema.json"
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
