import pytest

from core.models import (
    AuditEvent,
    Empresa,
    ReviewEvidence,
    ReviewItem,
    ReviewItemEvent,
    Usuario,
)
from core.review_items import (
    ReviewItemConflict,
    claim_review_item,
    create_review_item,
    dismiss_review_item,
    reopen_review_item,
    resolve_review_item,
)


@pytest.fixture
def session(setup_db):
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _empresa():
    return Empresa(
        nome_empresa="Empresa Revisão LTDA",
        cnpj_cpf="12345678000199",
        api_key="api-key-review",
        cod_dominio=9100,
    )


def test_create_review_item_groups_evidence_by_explicit_source_key(session):
    empresa = _empresa()
    session.add(empresa)
    session.commit()

    first = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="plano_snapshot",
        grouping_key="snapshot-conflict:2026-01-01",
        summary="Conflito de vigência",
        criticality="high",
        evidence=[
            {
                "source_type": "snapshot",
                "source_id": "snapshot-1",
                "summary": "Primeiro snapshot",
            }
        ],
    )
    second = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="plano_snapshot",
        grouping_key="snapshot-conflict:2026-01-01",
        summary="Conflito de vigência",
        criticality="high",
        evidence=[
            {
                "source_type": "snapshot",
                "source_id": "snapshot-2",
                "summary": "Segundo snapshot",
            }
        ],
    )

    assert first.id == second.id
    assert first.empresa_id == empresa.id
    assert first.status == "pending"
    assert {item.source_id for item in first.evidences} == {
        "snapshot-1",
        "snapshot-2",
    }


def test_review_item_models_are_registered_in_metadata():
    assert ReviewItem.__tablename__ == "review_items"
    assert ReviewEvidence.__tablename__ == "review_item_evidences"


def test_claim_is_exclusive_and_prevents_a_second_claimant(session):
    empresa = _empresa()
    first_user = Usuario(
        nome="Operador Um",
        login="operador.um",
        email="operador.um@example.com",
        senha_hash="hash",
        papel="operador",
    )
    second_user = Usuario(
        nome="Operador Dois",
        login="operador.dois",
        email="operador.dois@example.com",
        senha_hash="hash",
        papel="operador",
    )
    session.add_all([empresa, first_user, second_user])
    session.commit()
    item = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="manual_test",
        grouping_key="exclusive-claim",
        summary="Revisão necessária",
        criticality="medium",
        evidence=[{"source_type": "test", "source_id": "1", "summary": "Evidência"}],
    )

    claimed = claim_review_item(
        session, empresa_id=empresa.id, item_id=item.id, user_id=first_user.id
    )
    session.commit()

    assert claimed.status == "in_review"
    assert claimed.assignee_id == first_user.id
    with pytest.raises(ReviewItemConflict):
        claim_review_item(
            session, empresa_id=empresa.id, item_id=item.id, user_id=second_user.id
        )


@pytest.mark.parametrize("final_status", ["resolved", "dismissed"])
def test_reopening_final_item_clears_claim_and_audits_reason(session, final_status):
    empresa = _empresa()
    user = Usuario(
        nome="Operadora",
        login="operadora.review",
        email="operadora.review@example.com",
        senha_hash="hash",
        papel="operador",
    )
    session.add_all([empresa, user])
    session.commit()
    item = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="manual_test",
        grouping_key=f"reopen-{final_status}",
        summary="Revisão necessária",
        criticality="medium",
        evidence=[{"source_type": "test", "source_id": "2", "summary": "Evidência"}],
    )
    claim_review_item(session, empresa_id=empresa.id, item_id=item.id, user_id=user.id)
    if final_status == "resolved":
        resolve_review_item(
            session, empresa_id=empresa.id, item_id=item.id, user_id=user.id
        )
    else:
        dismiss_review_item(
            session,
            empresa_id=empresa.id,
            item_id=item.id,
            user_id=user.id,
            reason="Evidências incompatíveis",
        )
    session.commit()

    reopened = reopen_review_item(
        session,
        empresa_id=empresa.id,
        item_id=item.id,
        user_id=user.id,
        reason="Nova evidência disponível",
    )
    session.commit()
    session.refresh(reopened)

    assert reopened.status == "pending"
    assert reopened.assignee_id is None
    assert reopened.claimed_at is None
    assert reopened.resolved_at is None
    assert reopened.dismissed_at is None
    event = (
        session.query(ReviewItemEvent)
        .filter_by(review_item_id=item.id, event_type="reopened")
        .one()
    )
    audit = (
        session.query(AuditEvent)
        .filter_by(resource_id=str(item.id), event_type="review_item.reopened")
        .one()
    )
    assert event.from_status == final_status
    assert event.reason == "Nova evidência disponível"
    assert audit.metadata_json == {
        "transition_id": event.id,
        "from_status": final_status,
        "to_status": "pending",
    }
