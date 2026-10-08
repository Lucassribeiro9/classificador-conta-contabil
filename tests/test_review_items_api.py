from datetime import datetime, timedelta, timezone
from datetime import date

import jwt
import pytest

from core.config import settings
from core.models import AuditEvent, Empresa, RazaoAccountAlias, ReviewItem, ReviewItemEvent, Usuario, UsuarioEmpresaPermissao
from core.review_items import create_review_item
from core.plano_contas_snapshots import importar_snapshot


_seed_number = 9200


@pytest.fixture(autouse=True)
def jwt_settings():
    previous_secret = settings.JWT_SECRET_KEY
    previous_algorithm = settings.JWT_ALGORITHM
    settings.JWT_SECRET_KEY = "review-items-test-secret"
    settings.JWT_ALGORITHM = "HS256"
    try:
        yield
    finally:
        settings.JWT_SECRET_KEY = previous_secret
        settings.JWT_ALGORITHM = previous_algorithm


def _seed_user_company(permission="leitura"):
    global _seed_number
    from tests.conftest import TestingSessionLocal

    _seed_number += 1
    number = _seed_number
    empresa = Empresa(
        nome_empresa="Empresa da Central LTDA",
        cnpj_cpf=f"12345678{number:06d}",
        api_key=f"api-key-central-{number}",
        cod_dominio=number,
    )
    user = Usuario(
        nome="Ana Contadora",
        login=f"ana.central.{number}",
        email=f"ana.central.{number}@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="contador",
        is_active=True,
    )
    user.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permission)
    )
    with TestingSessionLocal() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.refresh(empresa)
        return user, empresa.id


def _create_item(empresa_id, *, grouping_key="case-1"):
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        item = create_review_item(
            session,
            empresa_id=empresa_id,
            source_type="snapshot_conflict",
            grouping_key=grouping_key,
            summary="Conflito de vigência",
            criticality="high",
            evidence=[
                {
                    "source_type": "snapshot",
                    "source_id": grouping_key,
                    "summary": "Referência segura do snapshot",
                }
            ],
        )
        session.commit()
        session.refresh(item)
        return item.id


def _auth_headers(user):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.papel,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_alias_confirmation_requires_claim_and_company_snapshot_target(client):
    from tests.conftest import TestingSessionLocal

    user, empresa_id = _seed_user_company(permission="operacao")
    with TestingSessionLocal() as session:
        imported = importar_snapshot(
            session, empresa_id=empresa_id,
            contas=[{"codigo": 100, "classificacao": "1.1", "nome": "Banco", "tipo": "A", "grau": 2}],
            vigencia=date(2026, 1, 1), origem="teste-api",
        )
        item = create_review_item(
            session, empresa_id=empresa_id, source_type="razao_account_unknown",
            grouping_key=f"{imported.snapshot.id}:200",
            summary="Conta observada fora do snapshot", criticality="high",
            evidence=[{"source_type": "razao_line", "source_id": "1:1", "summary": "Lote 1, linha 1"}],
        )
        item_id = item.id
        snapshot_id = imported.snapshot.id
        session.commit()

    base = f"/api/v1/companies/{empresa_id}/review-items/{item_id}"
    headers = _auth_headers(user)
    payload = {"target_codigo": 100, "reason": "Equivalência conferida"}
    assert client.post(f"{base}/confirm-razao-alias", headers=headers, json=payload).status_code == 409
    assert client.post(f"{base}/claim", headers=headers).status_code == 200
    assert client.post(
        f"{base}/confirm-razao-alias", headers=headers,
        json={"target_codigo": 999, "reason": "Conta inválida"},
    ).status_code == 409
    response = client.post(f"{base}/confirm-razao-alias", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    with TestingSessionLocal() as session:
        alias = session.query(RazaoAccountAlias).one()
        assert alias.empresa_id == empresa_id
        assert alias.snapshot_id == snapshot_id
        assert alias.observed_code == 200
        assert alias.target_codigo == 100


def test_razao_temporal_review_resolves_only_after_snapshot_becomes_applicable(client):
    from tests.conftest import TestingSessionLocal

    user, empresa_id = _seed_user_company(permission="operacao")
    with TestingSessionLocal() as session:
        item = create_review_item(
            session, empresa_id=empresa_id, source_type="razao_snapshot_missing",
            grouping_key="2026-01-02", summary="Plano sem snapshot aplicável",
            criticality="critical",
            evidence=[{"source_type": "razao_line", "source_id": "1:1", "summary": "Lote 1, linha 1"}],
        )
        item_id = item.id
        session.commit()
    base = f"/api/v1/companies/{empresa_id}/review-items/{item_id}"
    headers = _auth_headers(user)
    assert client.post(f"{base}/claim", headers=headers).status_code == 200
    assert client.post(f"{base}/resolve", headers=headers).status_code == 409

    with TestingSessionLocal() as session:
        importar_snapshot(
            session, empresa_id=empresa_id,
            contas=[{"codigo": 100, "classificacao": "1.1", "nome": "Banco", "tipo": "A", "grau": 2}],
            vigencia=date(2026, 1, 1), origem="teste-api",
        )
        session.commit()
    response = client.post(f"{base}/resolve", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_authorized_user_lists_only_company_review_items(client):
    user, empresa_id = _seed_user_company()
    other_user, other_empresa_id = _seed_user_company()
    expected_item_id = _create_item(empresa_id)
    _create_item(other_empresa_id, grouping_key="other-company")

    response = client.get(
        f"/api/v1/companies/{empresa_id}/review-items",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [expected_item_id]
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["limit"] == 100
    assert payload["has_next"] is False
    assert other_user.id != user.id


def test_read_permission_cannot_claim_review_item(client):
    user, empresa_id = _seed_user_company(permission="leitura")
    item_id = _create_item(empresa_id)

    response = client.post(
        f"/api/v1/companies/{empresa_id}/review-items/{item_id}/claim",
        headers=_auth_headers(user),
    )

    assert response.status_code == 403


def test_claim_conflict_is_audited_without_justification_metadata(client):
    user, empresa_id = _seed_user_company(permission="operacao")
    item_id = _create_item(empresa_id)
    url = f"/api/v1/companies/{empresa_id}/review-items/{item_id}/claim"
    headers = _auth_headers(user)

    first = client.post(url, headers=headers)
    second = client.post(url, headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "in_review"
    assert first.json()["assignee_id"] == user.id
    assert second.status_code == 409
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        item = session.get(ReviewItem, item_id)
        audit = session.query(AuditEvent).filter_by(event_type="review_item.claimed").one()
        event = session.query(ReviewItemEvent).filter_by(event_type="claimed").one()
        assert item.status == "in_review"
        assert audit.metadata_json == {
            "transition_id": event.id,
            "from_status": "pending",
            "to_status": "in_review",
        }


def test_company_admin_reassigns_to_authorized_operator_with_separate_audit_reason(client):
    user, empresa_id = _seed_user_company(permission="admin_empresa")
    item_id = _create_item(empresa_id, grouping_key="reassign-case")
    target = Usuario(
        nome="Operador Alvo",
        login="operador.alvo",
        email="operador.alvo@example.com",
        senha_hash="hash",
        papel="operador",
        is_active=True,
        permissoes_empresas=[
            UsuarioEmpresaPermissao(empresa_id=empresa_id, permissao="operacao")
        ],
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(target)
        session.commit()
        session.refresh(target)
        target_id = target.id

    url = f"/api/v1/companies/{empresa_id}/review-items/{item_id}"
    claim = client.post(f"{url}/claim", headers=_auth_headers(user))
    assert claim.status_code == 200
    reassigned = client.post(
        f"{url}/reassign",
        headers=_auth_headers(user),
        json={"assignee_id": target_id, "reason": "Distribuição da fila"},
    )

    assert reassigned.status_code == 200
    assert reassigned.json()["assignee_id"] == target_id
    assert "release" not in reassigned.json()["available_actions"]
    with TestingSessionLocal() as session:
        transition = (
            session.query(ReviewItemEvent)
            .filter_by(review_item_id=item_id, event_type="reassigned")
            .one()
        )
        audit = (
            session.query(AuditEvent)
            .filter_by(event_type="review_item.reassigned", resource_id=str(item_id))
            .one()
        )
        assert transition.reason == "Distribuição da fila"
        assert "reason" not in audit.metadata_json


def test_reassignment_rejects_operator_without_company_admin_permission(client):
    user, empresa_id = _seed_user_company(permission="operacao")
    item_id = _create_item(empresa_id, grouping_key="no-reassign-case")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/review-items/{item_id}/reassign",
        headers=_auth_headers(user),
        json={"assignee_id": user.id, "reason": "Motivo"},
    )

    assert response.status_code == 403


def test_assignee_candidates_only_include_active_operational_company_users(client):
    user, empresa_id = _seed_user_company(permission="admin_empresa")
    from tests.conftest import TestingSessionLocal

    target = Usuario(
        nome="Responsável Operacional",
        login="responsavel.operacional",
        email="responsavel.operacional@example.com",
        senha_hash="hash",
        papel="operador",
        is_active=True,
        permissoes_empresas=[
            UsuarioEmpresaPermissao(empresa_id=empresa_id, permissao="operacao")
        ],
    )
    outsider = Usuario(
        nome="Sem Acesso",
        login="sem.acesso",
        email="sem.acesso@example.com",
        senha_hash="hash",
        papel="operador",
        is_active=True,
    )
    inactive = Usuario(
        nome="Inativo",
        login="inativo",
        email="inativo@example.com",
        senha_hash="hash",
        papel="operador",
        is_active=False,
        permissoes_empresas=[
            UsuarioEmpresaPermissao(empresa_id=empresa_id, permissao="operacao")
        ],
    )
    with TestingSessionLocal() as session:
        session.add_all([target, outsider, inactive])
        session.commit()
        target_id = target.id
        outsider_id = outsider.id
        inactive_id = inactive.id

    response = client.get(
        f"/api/v1/companies/{empresa_id}/review-items/assignees",
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.json()["items"]}
    assert user.id in returned_ids
    assert target_id in returned_ids
    assert outsider_id not in returned_ids
    assert inactive_id not in returned_ids
