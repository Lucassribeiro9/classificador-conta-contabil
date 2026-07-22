from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import Empresa, Usuario, UsuarioEmpresaPermissao


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
        "nome": "Ana Admin",
        "login": "ana.admin",
        "email": "ana.admin@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "admin",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(sequence: int) -> Empresa:
    return Empresa(
        nome_empresa=f"Empresa {sequence} LTDA",
        cnpj_cpf=f"11222333000{sequence:03d}",
        api_key=f"api-key-{sequence}",
        cod_dominio=6200 + sequence,
        is_active=True,
    )


def _auth_headers(
    usuario: Usuario,
    *,
    expires_in: timedelta = timedelta(hours=12),
) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "role": usuario.papel,
            "type": "access",
            "iat": now,
            "exp": now + expires_in,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_global_admin_lists_all_companies_without_exposing_api_keys(client):
    from tests.conftest import TestingSessionLocal

    admin = _usuario()
    companies = [_empresa(1), _empresa(2)]
    with TestingSessionLocal() as session:
        session.add_all([admin, *companies])
        session.commit()
        session.refresh(admin)
        headers = _auth_headers(admin)
        expected = [
            {
                "id": company.id,
                "nome_empresa": company.nome_empresa,
                "cnpj_cpf": company.cnpj_cpf,
                "cod_dominio": company.cod_dominio,
                "is_active": True,
                "papel": "admin",
                "permissao": None,
            }
            for company in companies
        ]

    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code == 200
    assert response.json() == expected
    assert all("api_key" not in company for company in response.json())


def test_operator_lists_only_linked_company_with_effective_permission(client):
    from tests.conftest import TestingSessionLocal

    operator = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    allowed_company = _empresa(1)
    forbidden_company = _empresa(2)
    with TestingSessionLocal() as session:
        session.add_all([operator, allowed_company, forbidden_company])
        session.flush()
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=operator.id,
                empresa_id=allowed_company.id,
                permissao="operacao",
            )
        )
        session.commit()
        session.refresh(operator)
        headers = _auth_headers(operator)
        allowed_company_id = allowed_company.id
        forbidden_company_id = forbidden_company.id

    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": allowed_company_id,
            "nome_empresa": "Empresa 1 LTDA",
            "cnpj_cpf": "11222333000001",
            "cod_dominio": 6201,
            "is_active": True,
            "papel": "operador",
            "permissao": "operacao",
        }
    ]
    assert forbidden_company_id not in {
        company["id"] for company in response.json()
    }


def test_user_without_company_links_receives_empty_list(client):
    from tests.conftest import TestingSessionLocal

    accountant = _usuario(
        nome="Carla Contadora",
        login="carla.contadora",
        email="carla.contadora@example.com",
        papel="contador",
    )
    with TestingSessionLocal() as session:
        session.add_all([accountant, _empresa(1)])
        session.commit()
        session.refresh(accountant)
        headers = _auth_headers(accountant)

    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-API-Key": "api-key-1"},
        {"X-Admin-Token": "test-admin-token"},
        {"Authorization": "Bearer token-invalido"},
    ],
)
def test_authorized_companies_rejects_requests_without_valid_jwt(client, headers):
    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code in (401, 403)


def test_authorized_companies_rejects_expired_jwt(client):
    from tests.conftest import TestingSessionLocal

    user = _usuario()
    with TestingSessionLocal() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        headers = _auth_headers(user, expires_in=timedelta(seconds=-1))

    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "Token expirado"


def test_authorized_companies_rejects_inactive_user(client):
    from tests.conftest import TestingSessionLocal

    inactive_user = _usuario(is_active=False)
    with TestingSessionLocal() as session:
        session.add(inactive_user)
        session.commit()
        session.refresh(inactive_user)
        headers = _auth_headers(inactive_user)

    response = client.get("/api/v1/companies/authorized", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Usuário inativo"


def test_legacy_company_list_keeps_requiring_admin_token(
    client,
    admin_headers,
):
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(_empresa(1))
        session.commit()

    response_without_token = client.get("/api/v1/companies")
    response_with_token = client.get(
        "/api/v1/companies",
        headers=admin_headers,
    )

    assert response_without_token.status_code == 401
    assert response_with_token.status_code == 200
    assert response_with_token.json()[0]["api_key"] == "api-key-1"
