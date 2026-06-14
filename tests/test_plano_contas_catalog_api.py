from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import ContaContabil, Usuario


password_hash = PasswordHash.recommended()


@pytest.fixture(autouse=True)
def jwt_settings():
    previous_secret = settings.JWT_SECRET_KEY
    previous_algorithm = settings.JWT_ALGORITHM
    settings.JWT_SECRET_KEY = "test-secret"
    settings.JWT_ALGORITHM = "HS256"
    try:
        yield
    finally:
        settings.JWT_SECRET_KEY = previous_secret
        settings.JWT_ALGORITHM = previous_algorithm


def _usuario(**overrides) -> Usuario:
    data = {
        "nome": "Ana Contadora",
        "login": "ana.contadora",
        "email": "ana.contadora@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "contador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _conta(**overrides) -> ContaContabil:
    data = {
        "codigo": 10046,
        "classificacao": "1.1.01.01.02.10046",
        "nome": "BCO. SANTANDER",
        "tipo": "A",
        "grau": 6,
        "is_active": True,
        "is_financial_origin": True,
    }
    data.update(overrides)
    return ContaContabil(**data)


def _access_token(usuario: Usuario) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(usuario.id),
            "role": usuario.papel,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=12),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _auth_headers(usuario: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {_access_token(usuario)}"}


def _seed_catalog():
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    contas = [
        _conta(
            codigo=1000,
            classificacao="1",
            nome="ATIVO",
            tipo="S",
            grau=1,
            is_financial_origin=False,
        ),
        _conta(),
        _conta(
            codigo=20010,
            classificacao="2.1.01.01.20010",
            nome="FORNECEDORES",
            tipo="A",
            grau=5,
            is_financial_origin=False,
        ),
    ]
    with TestingSessionLocal() as session:
        session.add(usuario)
        session.add_all(contas)
        session.commit()
        session.refresh(usuario)
        return usuario


def test_authenticated_user_lists_catalog_accounts(client):
    usuario = _seed_catalog()

    response = client.get("/api/v1/plano-contas", headers=_auth_headers(usuario))

    assert response.status_code == 200
    data = response.json()
    assert [conta["codigo"] for conta in data] == [1000, 10046, 20010]
    assert data[1]["nome"] == "BCO. SANTANDER"
    assert data[1]["tipo"] == "A"


def test_catalog_list_filters_by_type(client):
    usuario = _seed_catalog()

    response = client.get(
        "/api/v1/plano-contas",
        params={"tipo": "S"},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert [conta["codigo"] for conta in response.json()] == [1000]


def test_catalog_list_filters_by_financial_origin_flag(client):
    usuario = _seed_catalog()

    response = client.get(
        "/api/v1/plano-contas",
        params={"is_financial_origin": True},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert [conta["codigo"] for conta in response.json()] == [10046]


def test_catalog_detail_returns_official_account_data_by_codigo(client):
    usuario = _seed_catalog()

    response = client.get(
        "/api/v1/plano-contas/10046",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["codigo"] == 10046
    assert response.json()["classificacao"] == "1.1.01.01.02.10046"
    assert response.json()["nome"] == "BCO. SANTANDER"
    assert response.json()["is_financial_origin"] is True


def test_catalog_detail_returns_official_account_data_by_id(client):
    usuario = _seed_catalog()

    list_response = client.get("/api/v1/plano-contas", headers=_auth_headers(usuario))
    assert list_response.status_code == 200
    conta_id = next(
        conta["id"] for conta in list_response.json() if conta["codigo"] == 10046
    )
    detail_response = client.get(
        f"/api/v1/plano-contas/id/{conta_id}",
        headers=_auth_headers(usuario),
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["codigo"] == 10046


def test_catalog_list_requires_jwt(client):
    response = client.get("/api/v1/plano-contas")

    assert response.status_code in (401, 403)
