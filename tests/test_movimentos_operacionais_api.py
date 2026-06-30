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


def _seed_operational_lote_with_movements(
    *,
    permissao: str = "leitura",
    empresa_overrides: dict | None = None,
    usuario_overrides: dict | None = None,
    lote_overrides: dict | None = None,
    movimentos: list[dict] | None = None,
):
    from tests.conftest import TestingSessionLocal

    empresa = _empresa(**(empresa_overrides or {}))
    usuario = _usuario(
        **(
            usuario_overrides
            or {
                "login": f"consulta.movimentos.{empresa.cod_dominio}",
                "email": f"consulta.movimentos.{empresa.cod_dominio}@example.com",
            }
        )
    )
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )
    lote_data = {
        "empresa": empresa,
        "usuario": usuario,
        "original_filename": "movimentos-consulta.xlsx",
        "file_hash": f"sha256:movimentos-consulta-{empresa.cod_dominio}",
        "status": "completed_with_warnings",
        "total_linhas": 2,
        "total_importadas": 2,
        "total_invalidas": 0,
        "warnings_metadata": {"warnings": []},
        "periodo_inicio": date(2026, 1, 1),
        "periodo_fim": date(2026, 1, 31),
        "cnpj_cpf_arquivo": empresa.cnpj_cpf,
        "codigo_dominio_arquivo": str(empresa.cod_dominio),
    }
    lote_data.update(lote_overrides or {})
    lote = LoteImportacaoMovimentoOperacional(**lote_data)
    movimentos_data = movimentos or [
        {
            "data": date(2026, 1, 2),
            "conta_financeira": 10046,
            "historico": "Pagamento fornecedor sensivel",
            "historico_normalizado": "pagamento fornecedor",
            "valor_original": -250.75,
            "valor_absoluto": 250.75,
            "direcao": "credito",
            "tipo_movimento": "saida",
            "documento": "DOC-SENSIVEL-001",
            "observacao": "Observacao sensivel",
            "contrapartida_informada": 20001,
            "status": "pre_classificado",
            "mensagens_validacao": [],
        },
        {
            "data": date(2026, 1, 3),
            "conta_financeira": 10046,
            "historico": "Transferencia sem contrapartida sensivel",
            "historico_normalizado": "transferencia sem contrapartida",
            "valor_original": -100,
            "valor_absoluto": 100,
            "direcao": "credito",
            "tipo_movimento": "transferencia",
            "documento": "DOC-SENSIVEL-002",
            "observacao": "Outra observacao sensivel",
            "contrapartida_informada": None,
            "status": "revisao",
            "mensagens_validacao": [
                "Tipo de movimento transferencia exige contrapartida."
            ],
        },
    ]

    with TestingSessionLocal() as session:
        session.add(lote)
        session.flush()
        for item in movimentos_data:
            session.add(
                MovimentoOperacionalImportado(
                    lote_id=lote.id,
                    empresa_id=empresa.id,
                    contrapartida_sugerida=None,
                    contrapartida_final=None,
                    confidence_sugerida=None,
                    elegivel_treino=False,
                    conta_debito=None,
                    conta_credito=None,
                    **item,
                )
            )
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.refresh(lote)
        return usuario, empresa.id, lote.id


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


def test_user_with_leitura_permission_lists_own_operational_lotes(client):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="leitura"
    )
    _seed_operational_lote_with_movements(
        empresa_overrides={
            "nome_empresa": "Outra Empresa Movimentos LTDA",
            "cnpj_cpf": "99888777000166",
            "api_key": "api-key-outra-movimentos",
            "cod_dominio": 2211,
        },
        usuario_overrides={
            "login": "consulta.movimentos.outra",
            "email": "consulta.movimentos.outra@example.com",
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes",
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
            "original_filename": "movimentos-consulta.xlsx",
            "status": "completed_with_warnings",
            "total_linhas": 2,
            "total_importadas": 2,
            "total_invalidas": 0,
            "periodo_inicio": "2026-01-01",
            "periodo_fim": "2026-01-31",
            "created_at": response.json()["items"][0]["created_at"],
        }
    ]


def test_user_lists_operational_movements_by_lote_and_status_without_raw_payload(
    client,
):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="leitura"
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos",
        params={"status": "revisao"},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"] == [
        {
            "id": response.json()["items"][0]["id"],
            "lote_id": lote_id,
            "empresa_id": empresa_id,
            "data": "2026-01-03",
            "conta_financeira": 10046,
            "historico_normalizado": "transferencia sem contrapartida",
            "valor_absoluto": "100.00",
            "direcao": "credito",
            "tipo_movimento": "transferencia",
            "contrapartida_informada": None,
            "contrapartida_sugerida": None,
            "contrapartida_final": None,
            "confidence_sugerida": None,
            "status": "revisao",
            "elegivel_treino": False,
            "mensagens_validacao": [
                "Tipo de movimento transferencia exige contrapartida."
            ],
            "conta_debito": None,
            "conta_credito": None,
        }
    ]
    item = response.json()["items"][0]
    assert "historico" not in item
    assert "documento" not in item
    assert "observacao" not in item
    assert "DOC-SENSIVEL-002" not in str(response.json())


def test_user_without_company_access_cannot_list_operational_lotes(client):
    from tests.conftest import TestingSessionLocal

    usuario = _usuario(login="sem.consulta.mov", email="sem.consulta.mov@example.com")
    _, empresa_id, _ = _seed_operational_lote_with_movements(permissao="leitura")
    with TestingSessionLocal() as session:
        session.add(usuario)
        session.commit()
        session.refresh(usuario)

    response = client.get(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso negado"


def test_operational_movements_query_does_not_cross_company_boundaries(client):
    usuario, empresa_id, _ = _seed_operational_lote_with_movements(permissao="leitura")
    _, outra_empresa_id, outro_lote_id = _seed_operational_lote_with_movements(
        empresa_overrides={
            "nome_empresa": "Empresa Sem Acesso Movimentos LTDA",
            "cnpj_cpf": "88777666000155",
            "api_key": "api-key-sem-acesso-movimentos",
            "cod_dominio": 3311,
        },
        usuario_overrides={
            "login": "consulta.movimentos.sem.acesso",
            "email": "consulta.movimentos.sem.acesso@example.com",
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{outro_lote_id}/movimentos",
        headers=_auth_headers(usuario),
    )

    assert outra_empresa_id != empresa_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Lote operacional não encontrado"


def test_user_with_operacao_permission_classifies_pending_operational_movements(
    client,
    monkeypatch,
):
    usuario, empresa_id, _ = _seed_operational_lote_with_movements(permissao="operacao")

    def fake_classificar(db, *, empresa_id, model_dir=None):
        return {
            "empresa_id": empresa_id,
            "quantidade_processada": 2,
            "total_sugerido": 1,
            "total_revisao": 1,
        }

    monkeypatch.setattr(
        "api.routes.movimentos_operacionais.classificar_movimentos_operacionais_pendentes",
        fake_classificar,
    )

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/classificar",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "empresa_id": empresa_id,
        "quantidade_processada": 2,
        "total_sugerido": 1,
        "total_revisao": 1,
    }


def test_classificar_movimentos_returns_controlled_error_when_model_is_missing(
    client,
    monkeypatch,
    tmp_path,
):
    from tests.conftest import TestingSessionLocal

    usuario, empresa_id, _ = _seed_operational_lote_with_movements(
        permissao="operacao",
        movimentos=[
            {
                "data": date(2026, 1, 3),
                "conta_financeira": 10046,
                "historico": "Pagamento pendente sensivel",
                "historico_normalizado": "pagamento pendente",
                "valor_original": -100,
                "valor_absoluto": 100,
                "direcao": "credito",
                "tipo_movimento": "saida",
                "documento": "DOC-SENSIVEL-MODELO-AUSENTE",
                "observacao": "Nao deve ir para auditoria",
                "contrapartida_informada": None,
                "status": "pendente",
                "mensagens_validacao": [],
            },
        ],
    )
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/classificar",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Modelo treinado não encontrado para a empresa"

    with TestingSessionLocal() as session:
        event = session.query(AuditEvent).one()

    assert event.event_type == "operational_movements.classification_failed"
    assert event.user_id == usuario.id
    assert event.empresa_id == empresa_id
    assert event.resource_id == "operational_movements_classification"
    assert event.metadata_json == {
        "total_pendentes": 1,
        "error_type": "ModelNotFound",
        "reason": "model_not_found",
    }
    assert "Pagamento pendente sensivel" not in str(event.metadata_json)
    assert "DOC-SENSIVEL-MODELO-AUSENTE" not in str(event.metadata_json)


def test_review_movimento_approve_success(client):
    from tests.conftest import TestingSessionLocal
    from core.models import ContaContabil
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="operacao")
    
    with TestingSessionLocal() as session:
        conta = ContaContabil(codigo=20001, classificacao="2.0.0", nome="Conta 20001", tipo="A", grau=3)
        session.add(conta)
        session.commit()
        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov_id = mov.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{mov_id}/review",
        json={"action": "approve", "conta_final": 20001},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "aprovado"
    assert response.json()["contrapartida_final"] == 20001


def test_review_movimento_reject_success(client):
    from tests.conftest import TestingSessionLocal
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="operacao")
    
    with TestingSessionLocal() as session:
        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov_id = mov.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{mov_id}/review",
        json={"action": "reject"},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejeitado"
    assert response.json()["contrapartida_final"] is None


def test_review_movimento_without_permission(client):
    from tests.conftest import TestingSessionLocal
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="leitura")
    
    with TestingSessionLocal() as session:
        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov_id = mov.id

    response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{mov_id}/review",
        json={"action": "approve", "conta_final": 20001},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Permissão insuficiente"
