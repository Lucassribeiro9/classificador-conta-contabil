from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import jwt
import pytest
from openpyxl import Workbook
from pwdlib import PasswordHash

from core.audit import record_audit_event
from core.config import settings
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    MovimentoOperacionalImportado,
    Usuario,
    UsuarioEmpresaPermissao,
)


password_hash = PasswordHash.recommended()


@pytest.fixture(autouse=True)
def jwt_settings():
    """Configura JWT previsivel para os testes de fluxo via API."""

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
    """Cria usuario interno autenticavel no fluxo operacional."""

    data = {
        "nome": "Flavia Fluxo",
        "login": "flavia.fluxo",
        "email": "flavia.fluxo@example.com",
        "senha_hash": password_hash.hash("senha-segura-123"),
        "papel": "operador",
        "is_active": True,
    }
    data.update(overrides)
    return Usuario(**data)


def _empresa(**overrides) -> Empresa:
    """Cria empresa para o fluxo operacional."""

    data = {
        "nome_empresa": "Empresa Fluxo Movimentos LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-fluxo-movimentos",
        "cod_dominio": 1122,
    }
    data.update(overrides)
    return Empresa(**data)


def _conta(codigo: int) -> ContaContabil:
    """Cria conta contabil analitica e ativa."""

    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
        is_active=True,
    )


def _vinculo(empresa_id: int, conta_codigo: int) -> EmpresaContaContabil:
    """Cria vinculo entre empresa e conta contabil."""

    return EmpresaContaContabil(
        empresa_id=empresa_id,
        conta_codigo=conta_codigo,
        quantidade_lancamentos=1,
        ultima_utilizacao=date(2026, 1, 1),
    )


def _auth_headers(usuario: Usuario) -> dict[str, str]:
    """Monta header bearer para o usuario persistido."""

    now = datetime.now(timezone.utc)
    token = jwt.encode(
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
    return {"Authorization": f"Bearer {token}"}


def _planilha_fluxo_operacional() -> bytes:
    """Gera planilha com linhas valida, pendente, revisao e invalida."""

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Movimentos"
    sheet.append(["Empresa", "Empresa Fluxo Movimentos LTDA"])
    sheet.append(["Codigo dominio", "9999"])
    sheet.append(["CNPJ/CPF", "11.222.333/0001-44"])
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
    sheet.append(
        [
            "03/01/2026",
            10046,
            "Pagamento pendente sensivel",
            -150.00,
            None,
            "saida",
            "DOC-SENSIVEL-002",
            "Outra observacao sensivel",
        ]
    )
    sheet.append(
        [
            "04/01/2026",
            10046,
            "Aplicacao sem contrapartida",
            -500.00,
            None,
            "aplicacao",
            "DOC-SENSIVEL-003",
            "Revisao esperada",
        ]
    )
    sheet.append(
        [
            "05/01/2026",
            10046,
            "Valor zero invalido",
            0,
            20001,
            "entrada",
            "DOC-SENSIVEL-004",
            "Invalida",
        ]
    )
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


def _upload_file() -> dict:
    """Monta upload multipart da planilha operacional."""

    return {
        "file": (
            "movimentos-fluxo.xlsx",
            _planilha_fluxo_operacional(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _seed_flow_data():
    """Persiste usuario, empresa, catalogo e vinculos para o fluxo."""

    from tests.conftest import TestingSessionLocal

    empresa = _empresa()
    outra_empresa = _empresa(
        nome_empresa="Outra Empresa Fluxo LTDA",
        cnpj_cpf="99888777000166",
        api_key="api-key-outra-fluxo",
        cod_dominio=9988,
    )
    usuario = _usuario()
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao="operacao")
    )
    with TestingSessionLocal() as session:
        session.add_all(
            [
                usuario,
                outra_empresa,
                _conta(10046),
                _conta(20001),
                _conta(30001),
            ]
        )
        session.flush()
        session.add_all([_vinculo(empresa.id, 10046), _vinculo(empresa.id, 20001)])
        session.commit()
        session.refresh(usuario)
        session.refresh(empresa)
        session.refresh(outra_empresa)
        return usuario, empresa.id, outra_empresa.id


def test_fluxo_operacional_importa_classifica_revisa_audita_e_isola_empresa(
    client,
    monkeypatch,
):
    """Cobre o fluxo principal de movimentos operacionais ponta a ponta."""

    from tests.conftest import TestingSessionLocal

    usuario, empresa_id, outra_empresa_id = _seed_flow_data()

    import_response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/import",
        files=_upload_file(),
        headers=_auth_headers(usuario),
    )

    assert import_response.status_code == 200
    assert import_response.json()["status"] == "completed_with_warnings"
    assert import_response.json()["total_linhas"] == 4
    assert import_response.json()["total_importadas"] == 3
    assert import_response.json()["total_invalidas"] == 1
    lote_id = import_response.json()["lote_id"]

    movimentos_response = client.get(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos",
        headers=_auth_headers(usuario),
    )

    assert movimentos_response.status_code == 200
    movimentos = movimentos_response.json()["items"]
    assert [movimento["status"] for movimento in movimentos] == [
        "pre_classificado",
        "pendente",
        "revisao",
    ]
    assert "historico" not in movimentos[0]
    assert "DOC-SENSIVEL" not in str(movimentos_response.json())
    pre_classificado_id = movimentos[0]["id"]
    pendente_id = movimentos[1]["id"]
    revisao_id = movimentos[2]["id"]

    def fake_classificar(db, *, empresa_id, model_dir=None):
        pendente = db.get(MovimentoOperacionalImportado, pendente_id)
        pendente.contrapartida_sugerida = 30001
        pendente.confidence_sugerida = 0.91
        pendente.status = "sugerido"
        record_audit_event(
            db,
            event_type="operational_movements.classified",
            empresa_id=empresa_id,
            resource_id="operational_movements_classification",
            metadata={
                "total_processado": 1,
                "total_sugerido": 1,
                "total_revisao": 0,
            },
        )
        return {
            "empresa_id": empresa_id,
            "quantidade_processada": 1,
            "total_sugerido": 1,
            "total_revisao": 0,
        }

    monkeypatch.setattr(
        "api.routes.movimentos_operacionais.classificar_movimentos_operacionais_pendentes",
        fake_classificar,
    )

    classify_response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/classificar",
        headers=_auth_headers(usuario),
    )

    assert classify_response.status_code == 200
    assert classify_response.json()["quantidade_processada"] == 1
    assert classify_response.json()["total_sugerido"] == 1

    approve_response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{pre_classificado_id}/review",
        json={"action": "approve", "conta_final": 20001},
        headers=_auth_headers(usuario),
    )
    correct_response = client.post(
        f"/api/v1/companies/{empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{pendente_id}/review",
        json={"action": "correct", "conta_final": 30001},
        headers=_auth_headers(usuario),
    )
    cross_company_response = client.get(
        f"/api/v1/companies/{outra_empresa_id}/movimentos-operacionais/lotes/{lote_id}/movimentos",
        headers=_auth_headers(usuario),
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "aprovado"
    assert approve_response.json()["contrapartida_final"] == 20001
    assert approve_response.json()["saldo_observado_original"] is None
    assert approve_response.json()["saldo_observado_decimal"] is None
    assert approve_response.json()["saldo_calculado_decimal"] == "-250.75"
    assert approve_response.json()["warnings_saldo"] == [
        "Saldo ausente; conferencia por saldo limitada para esta linha.",
        "Saldo inicial ausente; saldo calculado partiu de zero.",
    ]
    assert correct_response.status_code == 200
    assert correct_response.json()["status"] == "corrigido"
    assert correct_response.json()["contrapartida_final"] == 30001
    assert cross_company_response.status_code == 403
    assert cross_company_response.json()["message"] == "Acesso negado"

    with TestingSessionLocal() as session:
        movimentos_salvos = (
            session.query(MovimentoOperacionalImportado)
            .filter(MovimentoOperacionalImportado.lote_id == lote_id)
            .order_by(MovimentoOperacionalImportado.id.asc())
            .all()
        )
        event_types = [event.event_type for event in session.query(AuditEvent).all()]
        assert [movimento.status for movimento in movimentos_salvos] == [
            "aprovado",
            "corrigido",
            "revisao",
        ]
        assert movimentos_salvos[0].conta_debito == 20001
        assert movimentos_salvos[0].conta_credito == 10046
        assert movimentos_salvos[1].conta_debito == 30001
        assert movimentos_salvos[1].conta_credito == 10046
        assert movimentos_salvos[1].elegivel_treino is True
        assert movimentos_salvos[2].id == revisao_id
        assert event_types == [
            "operational_movements.imported",
            "operational_movements.classified",
            "operational_movements.aprovado",
            "empresa_conta.created_by_review",
            "operational_movements.corrigido",
        ]
        assert "Pagamento fornecedor sensivel" not in str(
            [event.metadata_json for event in session.query(AuditEvent).all()]
        )
        assert "DOC-SENSIVEL" not in str(
            [event.metadata_json for event in session.query(AuditEvent).all()]
        )
