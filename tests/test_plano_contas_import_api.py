from datetime import datetime, timedelta, timezone
from io import BytesIO

import jwt
import pytest
from openpyxl import Workbook
from pwdlib import PasswordHash

from core.config import settings
from core.models import Usuario


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


def _seed_user(usuario: Usuario) -> Usuario:
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(usuario)
        session.commit()
        session.refresh(usuario)
        return usuario


def _plano_contas_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Relatorio do Plano de Contas"])
    sheet.append([])
    sheet.append(["Codigo", "Tipo", "Classificacao", "Nome", "Grau"])
    sheet.append([1000, "S", "1", "ATIVO", 1])
    sheet.append([10046, "A", "1.1.01.01.02.10046", "BCO. SANTANDER", 6])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _upload_file(filename: str = "plano-contas.xlsx") -> dict:
    return {
        "file": (
            filename,
            _plano_contas_xlsx(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def test_admin_imports_plano_contas_and_receives_summary(client):
    admin = _seed_user(_usuario())

    response = client.post(
        "/api/v1/admin/plano-contas/import",
        files=_upload_file(),
        headers=_auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json() == {
        "criadas": 2,
        "atualizadas": 0,
        "ignoradas": 0,
        "invalidas": 0,
    }


def test_plano_contas_import_is_idempotent(client):
    admin = _seed_user(_usuario())
    headers = _auth_headers(admin)

    first_response = client.post(
        "/api/v1/admin/plano-contas/import",
        files=_upload_file(),
        headers=headers,
    )
    second_response = client.post(
        "/api/v1/admin/plano-contas/import",
        files=_upload_file(),
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == {
        "criadas": 0,
        "atualizadas": 0,
        "ignoradas": 2,
        "invalidas": 0,
    }


@pytest.mark.parametrize("papel", ["contador", "operador"])
def test_non_admin_cannot_import_plano_contas(client, papel):
    usuario = _seed_user(
        _usuario(
            nome=f"Usuario {papel}",
            login=f"usuario.{papel}",
            email=f"{papel}@example.com",
            papel=papel,
        )
    )

    response = client.post(
        "/api/v1/admin/plano-contas/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso restrito a administradores"


def test_plano_contas_import_requires_jwt(client):
    response = client.post(
        "/api/v1/admin/plano-contas/import",
        files=_upload_file(),
    )

    assert response.status_code in (401, 403)


def test_plano_contas_import_rejects_non_xlsx_file(client):
    admin = _seed_user(_usuario())

    response = client.post(
        "/api/v1/admin/plano-contas/import",
        files={"file": ("plano-contas.csv", b"codigo,tipo", "text/csv")},
        headers=_auth_headers(admin),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo deve ser .xlsx"
