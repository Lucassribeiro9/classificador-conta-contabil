from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import jwt
import pytest
from openpyxl import Workbook
from pwdlib import PasswordHash

from core.config import settings
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    FechamentoRazaoMensal,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
    UsuarioEmpresaPermissao,
)


password_hash = PasswordHash.recommended()
FIXTURES_DIR = Path(__file__).parent / "fixtures"
LEGACY_BALANCE_WARNING = {
    "linha": 1,
    "codigo": "saldo_ausente",
    "mensagem": "Saldo ausente; conferencia por saldo limitada para este bloco.",
    "detalhes": {
        "bloco_id": "bloco:1",
        "conta_codigo": 10046,
    },
    "warnings": [
        "Saldo ausente; conferencia por saldo limitada para este bloco."
    ],
}
DIVERGENT_BALANCE_WARNING = {
    "linha": 2,
    "codigo": "saldo_divergente",
    "mensagem": "Saldo observado diverge do saldo calculado para a conta do razao.",
    "detalhes": {
        "bloco_id": "bloco:1",
        "conta_codigo": 10046,
        "saldo_calculado": {"valor_decimal": "1000.00", "natureza": "D"},
        "saldo_observado": {
            "fonte": "saldo",
            "valor_decimal": "1250.75",
            "natureza": "D",
        },
    },
    "warnings": [
        "Saldo observado diverge do saldo calculado para a conta do razao."
    ],
}


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
        "login": "olivia.operadora",
        "email": "olivia.operadora@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Razao API LTDA",
        "cnpj_cpf": "22333444000155",
        "api_key": "api-key-razao-api",
        "cod_dominio": 9301,
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


def _razao_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Conta:", "10046", "BCO. SANTANDER"])
    sheet.append(["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"])
    sheet.append(["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _razao_xlsx_with_metadata(cnpj: str) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Empresa:", None, "Empresa Arquivo LTDA"])
    sheet.append(["C.N.P.J.:", None, cnpj])
    sheet.append(["Período:", None, "01/01/2026 - 31/12/2026"])
    sheet.append([])
    sheet.append(["Conta:", "10046", "BCO. SANTANDER"])
    sheet.append(
        ["Data", "Numero", "Historico", "Contrapartida", "Debito", "Credito"]
    )
    sheet.append(
        ["2026-01-02", "42", "Pagamento fornecedor", "20001", 250.75, None]
    )

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _upload_file(filename: str = "razao.xlsx", content: bytes | None = None) -> dict:
    return {
        "file": (
            filename,
            content if content is not None else _razao_xlsx(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _upload_file_with_metadata(cnpj: str, filename: str = "razao.xlsx") -> dict:
    return {
        "file": (
            filename,
            _razao_xlsx_with_metadata(cnpj),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _upload_fixture_file(filename: str) -> dict:
    return {
        "file": (
            filename,
            (FIXTURES_DIR / filename).read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _seed_user_company_and_catalog(
    permissao: str = "operacao",
    contas: tuple[int, ...] = (10046, 20001),
):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )
    with TestingSessionLocal() as session:
        session.add_all([usuario, *[_conta(codigo) for codigo in contas]])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        return usuario, empresa.id


def _seed_razao_lote_with_lancamento(
    *,
    permissao: str = "leitura",
    empresa_overrides: dict | None = None,
    lote_overrides: dict | None = None,
    lancamento_overrides: dict | None = None,
):
    from tests.conftest import TestingSessionLocal

    empresa = _empresa(**(empresa_overrides or {}))
    usuario = _usuario(
        login=f"operador.razao.{empresa.cod_dominio}",
        email=f"operador.razao.{empresa.cod_dominio}@example.com",
    )
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )
    lote_data = {
        "empresa": empresa,
        "usuario": usuario,
        "original_filename": "razao-consulta.xlsx",
        "file_hash": "sha256:razao-consulta",
        "status": "completed",
        "total_linhas": 1,
        "total_importadas": 1,
        "total_invalidas": 0,
        "warnings_metadata": {},
    }
    lote_data.update(lote_overrides or {})
    lote = LoteImportacaoRazao(**lote_data)
    lancamento_data = {
        "lote": lote,
        "empresa": empresa,
        "numero_lancamento": "42",
        "data": datetime(2026, 1, 2).date(),
        "conta_origem": 10046,
        "conta_contrapartida": 20001,
        "conta_debito": 10046,
        "conta_credito": 20001,
        "direcao": "debito",
        "historico": "Pagamento fornecedor confidencial",
        "historico_normalizado": "pagamento fornecedor",
        "valor": Decimal("250.75"),
    }
    lancamento_data.update(lancamento_overrides or {})
    lancamento = LancamentoRazaoNormalizado(**lancamento_data)

    with TestingSessionLocal() as session:
        session.add_all([usuario, lote, lancamento])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.refresh(lote)
        session.refresh(lancamento)
        return usuario, empresa.id, lote.id, lancamento.id


def test_user_with_operacao_permission_imports_razao_and_receives_summary(client):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "lote_id": 1,
        "status": "completed_with_warnings",
        "total_linhas": 1,
        "total_importadas": 1,
        "total_invalidas": 0,
        "warnings": [LEGACY_BALANCE_WARNING],
        "warnings_saldo": [LEGACY_BALANCE_WARNING],
    }


def test_user_with_leitura_permission_lists_own_razao_lotes_only(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura",
        lote_overrides={
            "warnings_metadata": {
                "warnings": [
                    LEGACY_BALANCE_WARNING,
                    {"linha": 9, "mensagem": "Warning genérico"},
                ]
            }
        },
    )
    _seed_razao_lote_with_lancamento(
        empresa_overrides={
            "nome_empresa": "Empresa Vizinha LTDA",
            "cnpj_cpf": "55444333000122",
            "api_key": "api-key-razao-vizinha",
            "cod_dominio": 9302,
        },
        lote_overrides={
            "original_filename": "razao-outra-empresa.xlsx",
            "file_hash": "sha256:razao-outra-empresa",
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 100
    assert response.json()["has_next"] is False
    assert response.json()["items"] == [
        {
            "id": lote_id,
            "empresa_id": empresa_id,
            "original_filename": "razao-consulta.xlsx",
            "status": "completed",
            "total_linhas": 1,
            "total_importadas": 1,
            "total_invalidas": 0,
            "warnings_saldo_total": 1,
            "created_at": response.json()["items"][0]["created_at"],
        }
    ]


def test_user_with_leitura_permission_lists_lote_lancamentos_without_raw_history(
    client,
):
    usuario, empresa_id, lote_id, lancamento_id = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/lancamentos",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"] == [
        {
            "id": lancamento_id,
            "lote_id": lote_id,
            "empresa_id": empresa_id,
            "numero_lancamento": "42",
            "data": "2026-01-02",
            "conta_origem": 10046,
            "conta_contrapartida": 20001,
            "conta_debito": 10046,
            "conta_credito": 20001,
            "direcao": "debito",
            "historico_normalizado": "pagamento fornecedor",
            "valor": "250.75",
        }
    ]
    assert "historico" not in response.json()["items"][0]


def test_user_with_leitura_permission_lists_lote_monthly_closings(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura",
        lote_overrides={"warnings_metadata": {"warnings": [LEGACY_BALANCE_WARNING]}},
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        fechamento = FechamentoRazaoMensal(
            lote_id=lote_id,
            empresa_id=empresa_id,
            conta_codigo=10046,
            ano=2026,
            mes=1,
            saldo_observado_original="1.250,75D",
            saldo_observado_decimal=Decimal("1250.75"),
            saldo_observado_natureza="D",
            saldo_observado_fonte="saldo_exercicio",
            saldo_calculado_decimal=Decimal("1000.00"),
            warnings_saldo=[DIVERGENT_BALANCE_WARNING],
        )
        session.add(fechamento)
        session.commit()
        session.refresh(fechamento)
        fechamento_id = fechamento.id

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lote_id"] == lote_id
    assert body["empresa_id"] == empresa_id
    assert body["status"] == "completed"
    assert body["warnings_saldo"] == [LEGACY_BALANCE_WARNING]
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["limit"] == 20
    assert body["has_next"] is False
    assert body["items"] == [
        {
            "id": fechamento_id,
            "lote_id": lote_id,
            "empresa_id": empresa_id,
            "conta_codigo": 10046,
            "ano": 2026,
            "mes": 1,
            "saldo_observado_original": "1.250,75D",
            "saldo_observado_decimal": "1250.75",
            "saldo_observado_natureza": "D",
            "saldo_observado_fonte": "saldo_exercicio",
            "saldo_calculado_decimal": "1000.00",
            "divergente": True,
            "warnings_saldo": [DIVERGENT_BALANCE_WARNING],
            "created_at": body["items"][0]["created_at"],
            "updated_at": body["items"][0]["updated_at"],
        }
    ]
    assert "saldo_calculado_natureza" not in body["items"][0]


def test_razao_closings_support_filters_and_stable_pagination(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add_all(
            [
                FechamentoRazaoMensal(
                    lote_id=lote_id,
                    empresa_id=empresa_id,
                    conta_codigo=conta_codigo,
                    ano=ano,
                    mes=mes,
                    saldo_observado_decimal=Decimal("100.00"),
                    saldo_calculado_decimal=Decimal("100.00"),
                    warnings_saldo=[],
                )
                for conta_codigo, ano, mes in [
                    (20001, 2026, 2),
                    (10046, 2026, 2),
                    (10046, 2026, 1),
                ]
            ]
        )
        session.commit()

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        params={"conta_codigo": 10046, "ano": 2026, "limit": 1, "page": 2},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page"] == 2
    assert response.json()["limit"] == 1
    assert response.json()["has_next"] is False
    assert [
        (item["conta_codigo"], item["ano"], item["mes"])
        for item in response.json()["items"]
    ] == [(10046, 2026, 2)]


    month_response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        params={"mes": 1, "limit": 100},
        headers=_auth_headers(usuario),
    )
    assert month_response.status_code == 200
    assert month_response.json()["limit"] == 100
    assert [item["mes"] for item in month_response.json()["items"]] == [1]

    excessive_limit_response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        params={"limit": 101},
        headers=_auth_headers(usuario),
    )
    assert excessive_limit_response.status_code == 422


def test_razao_closings_return_empty_page_for_lote_without_closings(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura",
        lote_overrides={"warnings_metadata": {"warnings": [LEGACY_BALANCE_WARNING]}},
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert response.json()["warnings_saldo"] == [LEGACY_BALANCE_WARNING]


def test_razao_closings_require_authentication(client):
    _, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento()

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos"
    )

    assert response.status_code == 401


def test_razao_closings_reject_user_without_company_access(client):
    usuario_sem_acesso = _usuario(
        login="sem.acesso.fechamentos",
        email="sem.acesso.fechamentos@example.com",
    )
    _, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento()
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(usuario_sem_acesso)
        session.commit()
        session.refresh(usuario_sem_acesso)

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/fechamentos",
        headers=_auth_headers(usuario_sem_acesso),
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso negado"


def test_razao_closings_do_not_cross_company_boundaries(client):
    usuario, empresa_id, _, _ = _seed_razao_lote_with_lancamento()
    _, outra_empresa_id, outro_lote_id, _ = _seed_razao_lote_with_lancamento(
        empresa_overrides={
            "nome_empresa": "Empresa Fechamento Vizinha LTDA",
            "cnpj_cpf": "77888999000100",
            "api_key": "api-key-fechamento-vizinha",
            "cod_dominio": 9304,
        },
        lote_overrides={
            "original_filename": "razao-fechamento-vizinha.xlsx",
            "file_hash": "sha256:razao-fechamento-vizinha",
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{outro_lote_id}/fechamentos",
        headers=_auth_headers(usuario),
    )

    assert outra_empresa_id != empresa_id
    assert response.status_code == 404
    assert response.json()["message"] == "Lote de razão não encontrado"


def test_user_without_company_link_cannot_list_razao_lotes(client):
    usuario = _usuario(
        login="usuario.sem.razao",
        email="usuario.sem.razao@example.com",
    )
    _, empresa_id, _, _ = _seed_razao_lote_with_lancamento(permissao="leitura")
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as session:
        session.add(usuario)
        session.commit()
        session.refresh(usuario)

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso negado"


def test_razao_lancamentos_query_does_not_cross_company_boundaries(client):
    usuario, empresa_id, _, _ = _seed_razao_lote_with_lancamento(permissao="leitura")
    _, outra_empresa_id, outro_lote_id, _ = _seed_razao_lote_with_lancamento(
        empresa_overrides={
            "nome_empresa": "Empresa Sem Acesso LTDA",
            "cnpj_cpf": "66777888000199",
            "api_key": "api-key-sem-acesso",
            "cod_dominio": 9303,
        },
        lote_overrides={
            "original_filename": "razao-sem-acesso.xlsx",
            "file_hash": "sha256:razao-sem-acesso",
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{outro_lote_id}/lancamentos",
        headers=_auth_headers(usuario),
    )

    assert outra_empresa_id != empresa_id
    assert response.status_code == 404
    assert response.json()["message"] == "Lote de razão não encontrado"


def test_user_imports_valid_tabular_fixture_through_endpoint(client):
    usuario, empresa_id = _seed_user_company_and_catalog(
        "operacao",
        contas=(10046, 20102, 30102, 20104),
    )

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_fixture_file("razao_lote_valido.xlsx"),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["total_linhas"] == 3
    assert response.json()["total_importadas"] == 3
    assert response.json()["total_invalidas"] == 0
    assert response.json()["warnings"] == []


def test_razao_import_rejects_file_cnpj_from_another_company(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file_with_metadata("11.222.333/0001-44"),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 400
    assert (
        response.json()["message"]
        == "CNPJ do razao nao corresponde a empresa da importacao."
    )

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.import_failed"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["reason"] == "company_mismatch"
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert "11222333000144" not in str(event.metadata_json)
        assert session.query(LoteImportacaoRazao).count() == 0
        assert session.query(LancamentoRazaoNormalizado).count() == 0


def test_user_imports_tabular_fixture_with_controlled_warnings_through_endpoint(
    client,
):
    usuario, empresa_id = _seed_user_company_and_catalog(
        "operacao",
        contas=(10046, 20101),
    )

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_fixture_file("razao_lote_com_warnings.xlsx"),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed_with_warnings"
    assert response.json()["total_linhas"] == 3
    assert response.json()["total_importadas"] == 1
    assert response.json()["total_invalidas"] == 2
    assert response.json()["warnings"] == [
        {
            "linha": 2,
            "warnings": ["Linha do razao sem contrapartida valida."],
        },
        {
            "linha": 3,
            "warnings": [
                "Conta de contrapartida 99999 nao encontrada no catalogo."
            ],
        },
    ]


def test_successful_razao_import_creates_audit_event_with_counters(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.imported"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.resource_id == str(response.json()["lote_id"])
        assert event.metadata_json["total_linhas"] == 1
        assert event.metadata_json["total_importadas"] == 1
        assert event.metadata_json["total_invalidas"] == 0
        assert event.metadata_json["warnings"] == [LEGACY_BALANCE_WARNING]
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert "Pagamento fornecedor" not in str(event.metadata_json)


def test_duplicate_razao_file_hash_creates_failed_audit_event(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("operacao")
    headers = _auth_headers(usuario)
    file_content = _razao_xlsx()

    first_response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(content=file_content),
        headers=headers,
    )
    second_response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(content=file_content),
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert second_response.json()["message"] == "Arquivo ja importado com sucesso para esta empresa."

    with TestingSessionLocal() as session:
        events = session.query(AuditEvent).order_by(AuditEvent.id).all()
        assert [event.event_type for event in events] == [
            "ledger.imported",
            "ledger.import_failed",
        ]
        failed_event = events[-1]
        assert failed_event.user_id == usuario.id
        assert failed_event.empresa_id == empresa_id
        assert failed_event.metadata_json["file_hash"].startswith("sha256:")
        assert failed_event.metadata_json["error_type"] == "RazaoImportError"
        assert failed_event.metadata_json["reason"] == "duplicate_file_hash"
        assert "Traceback" not in failed_event.metadata_json["error"]


def test_user_with_admin_empresa_permission_imports_razao(client):
    usuario, empresa_id = _seed_user_company_and_catalog("admin_empresa")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed_with_warnings"
    assert response.json()["total_importadas"] == 1


def test_user_with_leitura_permission_cannot_import_razao(client):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id = _seed_user_company_and_catalog("leitura")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Permissão insuficiente"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.import_denied"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert event.metadata_json["reason"] == "insufficient_permission"


def test_user_without_company_link_cannot_import_razao(client):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario()
    empresa = _empresa()
    with TestingSessionLocal() as session:
        session.add_all([usuario, empresa, _conta(10046), _conta(20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        headers = _auth_headers(usuario)
        empresa_id = empresa.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Acesso negado"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()
        assert event.event_type == "ledger.import_denied"
        assert event.user_id == usuario.id
        assert event.empresa_id == empresa_id
        assert event.metadata_json["file_hash"].startswith("sha256:")
        assert event.metadata_json["reason"] == "access_denied"
        assert "Pagamento fornecedor" not in str(event.metadata_json)


def test_razao_import_rejects_non_xlsx_file(client):
    usuario, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files={"file": ("razao.csv", b"Conta:,10046", "text/csv")},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Arquivo deve ser .xlsx"


def test_razao_import_requires_jwt(client):
    _, empresa_id = _seed_user_company_and_catalog("operacao")

    response = client.post(
        f"/api/v1/companies/{empresa_id}/razao/import",
        files=_upload_file(),
    )

    assert response.status_code in (401, 403)
