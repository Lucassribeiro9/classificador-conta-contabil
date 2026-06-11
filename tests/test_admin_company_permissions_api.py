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


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Auth LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-auth",
        "cod_dominio": 6201,
    }
    data.update(overrides)
    return Empresa(**data)


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


def _seed_admin_user_and_company():
    from tests.conftest import TestingSessionLocal

    admin = _usuario()
    usuario = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([admin, usuario, empresa])
        session.commit()
        session.refresh(admin)
        session.refresh(usuario)
        session.refresh(empresa)
        return admin, usuario.id, empresa.id


def test_admin_links_user_to_company_with_valid_permission(client):
    admin, usuario_id, empresa_id = _seed_admin_user_and_company()

    response = client.post(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        json={"permissao": "operacao"},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["usuario_id"] == usuario_id
    assert data["empresa_id"] == empresa_id
    assert data["permissao"] == "operacao"


def test_admin_updates_existing_company_permission(client):
    admin, usuario_id, empresa_id = _seed_admin_user_and_company()
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                permissao="leitura",
            )
        )
        session.commit()

    response = client.patch(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        json={"permissao": "admin_empresa"},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["permissao"] == "admin_empresa"


def test_admin_removes_company_permission(client):
    admin, usuario_id, empresa_id = _seed_admin_user_and_company()
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                permissao="operacao",
            )
        )
        session.commit()

    delete_response = client.delete(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        headers=_auth_headers(admin),
    )
    update_response = client.patch(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        json={"permissao": "leitura"},
        headers=_auth_headers(admin),
    )

    assert delete_response.status_code == 204
    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "Vínculo não encontrado"


def test_admin_permission_rejects_invalid_permission(client):
    admin, usuario_id, empresa_id = _seed_admin_user_and_company()

    response = client.post(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        json={"permissao": "dono"},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 422


def test_non_admin_cannot_manage_company_permissions(client):
    from tests.conftest import TestingSessionLocal

    contador = _usuario(
        nome="Caio Contador",
        login="caio.contador",
        email="caio.contador@example.com",
        papel="contador",
    )
    usuario = _usuario(
        nome="Bruno Operador",
        login="bruno.operador",
        email="bruno.operador@example.com",
        papel="operador",
    )
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([contador, usuario, empresa])
        session.commit()
        session.refresh(contador)
        session.refresh(usuario)
        session.refresh(empresa)
        headers = _auth_headers(contador)
        usuario_id = usuario.id
        empresa_id = empresa.id

    response = client.post(
        f"/api/v1/admin/users/{usuario_id}/companies/{empresa_id}/permissions",
        json={"permissao": "leitura"},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso restrito a administradores"
