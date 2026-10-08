"""Importação contextual e autorização da resolução temporal."""

from datetime import datetime, timedelta, timezone
from io import BytesIO

import jwt
from openpyxl import Workbook

from core.config import settings
from core.models import Empresa, Usuario, UsuarioEmpresaPermissao
from tests.conftest import TestingSessionLocal


def _xlsx(nome):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Codigo", "Tipo", "Classificacao", "Nome", "Grau"])
    sheet.append([100, "A", "1.1", nome, 2])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _seed():
    with TestingSessionLocal() as session:
        empresa = Empresa(
            nome_empresa="Plano API",
            api_key="plano-api",
            cnpj_cpf="00000000000193",
            cod_dominio=993,
        )
        outsider = Empresa(
            nome_empresa="Outra empresa",
            api_key="plano-api-other",
            cnpj_cpf="00000000000194",
            cod_dominio=994,
        )
        user = Usuario(
            nome="Contador",
            login="contador.plano",
            email="plano@test.local",
            senha_hash="test",
            papel="contador",
            is_active=True,
        )
        session.add_all([empresa, outsider, user])
        session.flush()
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=user.id, empresa_id=empresa.id, permissao="operacao"
            )
        )
        session.commit()
        return empresa.id, outsider.id, user.id


def _headers(user_id):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "contador",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_importacao_por_empresa_restringe_acesso_e_conflito(client):
    company_id, outsider_id, user_id = _seed()
    url = f"/api/v1/empresas/{company_id}/plano-contas/snapshots/import"
    payload = {"vigencia": "2026-02-01", "origem": "arquivo-sintetico"}
    first = client.post(
        url,
        headers=_headers(user_id),
        data=payload,
        files={
            "file": (
                "plano.xlsx",
                _xlsx("Banco"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert first.status_code == 200, first.text
    second = client.post(
        url,
        headers=_headers(user_id),
        data=payload,
        files={
            "file": (
                "plano.xlsx",
                _xlsx("Despesa"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["review_item_id"] is not None
    inspected = client.get(
        f"/api/v1/empresas/{company_id}/plano-contas/snapshots/{first.json()['snapshot_id']}",
        headers=_headers(user_id),
    )
    assert inspected.status_code == 200
    assert inspected.json()["content"][0]["nome"] == "Banco"
    assert inspected.json()["imports"][0]["origem"] == "arquivo-sintetico"
    assert inspected.json()["imports"][0]["vigencia"] == "2026-02-01"
    assert (
        client.get(
            f"/api/v1/empresas/{company_id}/plano-contas/snapshots/at/2026-03-01",
            headers=_headers(user_id),
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/empresas/{outsider_id}/plano-contas/snapshots/import",
            headers=_headers(user_id),
            data=payload,
            files={"file": ("plano.xlsx", _xlsx("Banco"))},
        ).status_code
        == 403
    )
    item_id = second.json()["review_item_id"]
    review_url = f"/api/v1/companies/{company_id}/review-items/{item_id}"
    assert (
        client.post(review_url + "/claim", headers=_headers(user_id)).status_code == 200
    )
    assert (
        client.post(review_url + "/resolve", headers=_headers(user_id)).status_code
        == 409
    )
    resolved = client.post(
        f"/api/v1/empresas/{company_id}/plano-contas/snapshots/conflicts/{item_id}/resolve",
        headers=_headers(user_id),
        json={"snapshot_id": first.json()["snapshot_id"], "reason": "Plano verificado"},
    )
    assert resolved.status_code == 200, resolved.text
    selected = client.get(
        f"/api/v1/empresas/{company_id}/plano-contas/snapshots/at/2026-03-01",
        headers=_headers(user_id),
    )
    assert selected.status_code == 200
    assert selected.json()["id"] == first.json()["snapshot_id"]
    decision = client.get(
        f"/api/v1/empresas/{company_id}/plano-contas/snapshots/conflicts/{item_id}/decision",
        headers=_headers(user_id),
    )
    assert decision.status_code == 200
    assert decision.json()["user_id"] == user_id
    assert decision.json()["reason"] == "Plano verificado"
    assert sorted(decision.json()["snapshot_ids"]) == sorted(
        [first.json()["snapshot_id"], second.json()["snapshot_id"]]
    )
