from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import jwt
import pytest
from openpyxl import Workbook
from pwdlib import PasswordHash

from core.config import settings
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Usuario,
    UsuarioEmpresaPermissao,
)


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
        "nome": "Olivia Operadora",
        "login": "olivia.movimentos",
        "email": "olivia.movimentos@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Movimentos LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-movimentos",
        "cod_dominio": 1122,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(codigo: int) -> ContaContabil:
    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
        is_active=True,
    )


def _vinculo(empresa_id: int, conta_codigo: int) -> EmpresaContaContabil:
    return EmpresaContaContabil(
        empresa_id=empresa_id,
        conta_codigo=conta_codigo,
        quantidade_lancamentos=1,
        ultima_utilizacao=date(2026, 1, 1),
    )


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


def _movimentos_xlsx(cnpj_cpf: str = "11.222.333/0001-44") -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Movimentos"
    sheet.append(["Empresa", "Empresa Movimentos LTDA"])
    sheet.append(["Codigo dominio", "1122"])
    sheet.append(["CNPJ/CPF", cnpj_cpf])
    sheet.append(["Periodo inicio", "01/01/2026"])
    sheet.append(["Periodo fim", "31/01/2026"])
    sheet.append([])
    sheet.append(
        [
            "data",
            "conta_financeira",
            "historico",
            "valor",
            "contrapartida",
            "tipo_movimento",
            "documento",
            "observacao",
        ]
    )
    sheet.append(
        [
            "02/01/2026",
            10046,
            "Pagamento fornecedor sensivel",
            -250.75,
            20001,
            "saida",
            "DOC-SENSIVEL-001",
            "Observacao sensivel",
        ]
    )

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _upload_file(filename: str = "movimentos.xlsx") -> dict:
    return {
        "file": (
            filename,
            _movimentos_xlsx(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _seed_user_company_catalog_and_links(permissao: str = "operacao"):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )
    contas = [_conta(10046), _conta(20001)]
    with TestingSessionLocal() as session:
        session.add_all([usuario, *contas])
        session.flush()
        session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        return usuario, empresa.id


def test_user_with_operacao_permission_imports_operational_movements(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_catalog_and_links("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "lote_id": 1,
        "status": "completed",
        "total_linhas": 1,
        "total_importadas": 1,
        "total_invalidas": 0,
        "warnings": [],
    }

    with TestingSessionLocal() as session:
        lote = session.query(LoteImportacaoMovimentoOperacional).one()
        movimento = session.query(MovimentoOperacionalImportado).one()
        event = session.query(AuditEvent).one()
        assert lote.empresa_id == empresa_id
        assert movimento.empresa_id == empresa_id
        assert movimento.status == "pre_classificado"
        assert event.event_type == "operational_movements.imported"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.resource_id == str(lote.id)
        assert event.metadata_json["total_importadas"] == 1
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert "Pagamento fornecedor sensivel" not in str(event.metadata_json)
        assert "DOC-SENSIVEL-001" not in str(event.metadata_json)


def test_user_without_company_access_cannot_import_operational_movements(client):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario(login="sem.acesso.movimentos", email="sem.acesso@example.com")
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, _conta(10046), _conta(20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        empresa_id = empresa.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "operational_movements.import_denied"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["reason"] == "access_denied"
        assert "Pagamento fornecedor sensivel" not in str(event.metadata_json)
        assert session.query(LoteImportacaoMovimentoOperacional).count() == 0
        assert session.query(MovimentoOperacionalImportado).count() == 0


def test_operational_movements_import_rejects_non_xlsx_file(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_catalog_and_links("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/import",
        files={"file": ("movimentos.csv", b"data,historico", "text/csv")},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo deve ser .xlsx"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "operational_movements.import_failed"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["reason"] == "invalid_file_type"
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert "data,historico" not in str(event.metadata_json)
