import pytest

from api.main import app
from core.config import settings
from core.models import (
    Empresa,
    IdentidadeServico,
    IdentidadeServicoEmpresa,
    IdentidadeServicoEscopo,
    LoteImportacaoRazao,
    WarningImportacaoRazao,
)
from core.service_credentials import emitir_credencial_servico
from tests.conftest import TestingSessionLocal
from tests.test_razao_import_api import (
    _auth_headers,
    _seed_razao_lote_with_lancamento,
    _usuario,
)


def test_reader_lists_normalized_warnings_with_stable_pagination(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    with TestingSessionLocal.begin() as session:
        session.add_all(
            [
                WarningImportacaoRazao(
                    lote_id=lote_id,
                    linha=10,
                    codigo="saldo_divergente",
                    mensagem="Primeiro aviso seguro.",
                    detalhes={"bloco_id": "bloco:1"},
                ),
                WarningImportacaoRazao(
                    lote_id=lote_id,
                    linha=11,
                    codigo="conta_nao_encontrada",
                    mensagem="Segundo aviso seguro.",
                    detalhes={},
                ),
            ]
        )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        params={"page": 2, "limit": 1},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "source": "normalized",
        "items": [
            {
                "linha": 11,
                "codigo": "conta_nao_encontrada",
                "mensagem": "Segundo aviso seguro.",
                "detalhes": {},
            }
        ],
        "total": 2,
        "page": 2,
        "limit": 1,
        "has_next": False,
    }


def test_reader_lists_flattened_legacy_warnings_with_same_public_shape(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura",
        lote_overrides={
            "warnings_metadata": {
                "warnings": [
                    {
                        "linha": 7,
                        "warnings": [
                            "Lancamento sem contrapartida.",
                            "Conta 999 nao encontrada no catalogo.",
                        ],
                    },
                    {
                        "linha": 8,
                        "codigo": "saldo_ausente",
                        "mensagem": "Saldo ausente para conferencia.",
                        "detalhes": {"bloco_id": "bloco:8"},
                    },
                ]
            }
        },
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json() == {
        "source": "legacy",
        "items": [
            {
                "linha": 7,
                "codigo": "contrapartida_ausente",
                "mensagem": "Lancamento sem contrapartida.",
                "detalhes": {},
            },
            {
                "linha": 7,
                "codigo": "conta_nao_encontrada",
                "mensagem": "Conta 999 nao encontrada no catalogo.",
                "detalhes": {},
            },
            {
                "linha": 8,
                "codigo": "saldo_ausente",
                "mensagem": "Saldo ausente para conferencia.",
                "detalhes": {"bloco_id": "bloco:8"},
            },
        ],
        "total": 3,
        "page": 1,
        "limit": 20,
        "has_next": False,
    }


def test_authorized_service_lists_company_warnings(client, monkeypatch):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    monkeypatch.setattr(settings, "SERVICE_CREDENTIAL_SECRET", "service-test-secret")
    with TestingSessionLocal.begin() as session:
        identidade = IdentidadeServico(
            identifier="n8n-razao-read",
            nome="Integração Razão",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
            empresas=[IdentidadeServicoEmpresa(empresa_id=empresa_id)],
            escopos=[IdentidadeServicoEscopo(escopo="empresas:read")],
        )
        session.add(identidade)
        session.flush()
        credential = emitir_credencial_servico(session, identidade_id=identidade.id)
        outra_empresa = Empresa(
            nome_empresa="Outra empresa",
            cnpj_cpf="33444555000166",
            api_key="api-key-outra-warnings",
            cod_dominio=9302,
        )
        session.add(outra_empresa)
        session.flush()
        outro_lote = LoteImportacaoRazao(
            empresa_id=outra_empresa.id,
            usuario_id=usuario.id,
            original_filename="outro.xlsx",
            file_hash="sha256:outro-warnings",
            status="completed",
            total_linhas=0,
        )
        session.add(outro_lote)
        session.flush()
        outra_empresa_id = outra_empresa.id
        outro_lote_id = outro_lote.id

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers={"X-Service-Credential": credential.secret},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "normalized"
    forbidden = client.get(
        f"/api/v1/companies/{outra_empresa_id}/razao/lotes/{outro_lote_id}/warnings",
        headers={"X-Service-Credential": credential.secret},
    )
    assert forbidden.status_code == 403


def test_normalized_warning_details_do_not_expose_unapproved_fields(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    with TestingSessionLocal.begin() as session:
        session.add(
            WarningImportacaoRazao(
                lote_id=lote_id,
                linha=3,
                codigo="saldo_divergente",
                mensagem="Saldo divergente.",
                detalhes={
                    "bloco_id": "bloco:3",
                    "conta_codigo": 10046,
                    "saldo_observado": {
                        "valor_decimal": "10.00",
                        "natureza": "D",
                        "payload": "não expor",
                    },
                    "path": "/private/upload.xlsx",
                    "raw_payload": {"historico": "não expor"},
                },
            )
        )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["detalhes"] == {
        "bloco_id": "bloco:3",
        "conta_codigo": 10046,
        "saldo_observado": {"valor_decimal": "10.00", "natureza": "D"},
    }


@pytest.mark.parametrize("source", ["normalized", "legacy"])
def test_warning_filters_are_applied_before_total_and_pagination(client, source):
    metadata = (
        {
            "warnings": [
                {
                    "linha": 4,
                    "codigo": "saldo_ausente",
                    "mensagem": "Outro aviso.",
                },
                {
                    "linha": 5,
                    "codigo": "saldo_ausente",
                    "mensagem": "Aviso filtrado.",
                },
                {
                    "linha": 5,
                    "codigo": "saldo_divergente",
                    "mensagem": "Código diferente.",
                },
            ]
        }
        if source == "legacy"
        else {"totals_by_code": {"saldo_ausente": 2, "saldo_divergente": 1}}
    )
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura", lote_overrides={"warnings_metadata": metadata}
    )
    if source == "normalized":
        with TestingSessionLocal.begin() as session:
            session.add_all(
                [
                    WarningImportacaoRazao(
                        lote_id=lote_id,
                        linha=linha,
                        codigo=codigo,
                        mensagem=mensagem,
                        detalhes={},
                    )
                    for linha, codigo, mensagem in [
                        (4, "saldo_ausente", "Outro aviso."),
                        (5, "saldo_ausente", "Aviso filtrado."),
                        (5, "saldo_divergente", "Código diferente."),
                    ]
                ]
            )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        params={"codigo": "saldo_ausente", "linha": 5, "page": 1, "limit": 1},
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["source"] == source
    assert response.json()["total"] == 1
    assert response.json()["has_next"] is False
    assert response.json()["items"][0]["mensagem"] == "Aviso filtrado."


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_active_lote_does_not_expose_warnings(client, status):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    with TestingSessionLocal.begin() as session:
        lote = session.get(LoteImportacaoRazao, lote_id)
        lote.status = status
        lote.total_linhas = None
        lote.linhas_processadas = 0
        lote.total_importadas = 0
        lote.total_invalidas = 0

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Resultados ainda não estão disponíveis"


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"limit": 0}, {"limit": 101}, {"linha": 0}],
)
def test_warning_pagination_rejects_invalid_parameters(client, params):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        params=params,
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 422


def test_warning_endpoint_enforces_company_access_and_rejects_ambiguous_auth(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    sem_acesso = _usuario(
        login="sem.acesso.warnings",
        email="sem.acesso.warnings@example.com",
    )
    with TestingSessionLocal.begin() as session:
        session.add(sem_acesso)
        session.flush()
        forbidden_headers = _auth_headers(sem_acesso)
    forbidden = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=forbidden_headers,
    )
    ambiguous = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers={**_auth_headers(usuario), "X-Service-Credential": "svc_ambiguous"},
    )

    assert forbidden.status_code == 403
    assert ambiguous.status_code == 400


def test_empty_new_lote_uses_normalized_source(client):
    usuario, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura",
        lote_overrides={"warnings_metadata": {"totals_by_code": {}}},
    )

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=_auth_headers(usuario),
    )

    assert response.status_code == 200
    assert response.json()["source"] == "normalized"
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_global_admin_lists_company_warnings_without_explicit_link(client):
    _, empresa_id, lote_id, _ = _seed_razao_lote_with_lancamento(
        permissao="leitura"
    )
    admin = _usuario(
        login="admin.warnings",
        email="admin.warnings@example.com",
        papel="admin",
    )
    with TestingSessionLocal.begin() as session:
        session.add(admin)
        session.flush()
        headers = _auth_headers(admin)

    response = client.get(
        f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
        headers=headers,
    )

    assert response.status_code == 200


def test_warning_contract_is_published_in_openapi(client):
    app.openapi_schema = None
    operation = client.get("/openapi.json").json()["paths"][
        "/api/v1/companies/{company_id}/razao/lotes/{lote_id}/warnings"
    ]["get"]

    assert {parameter["name"] for parameter in operation["parameters"]} >= {
        "company_id",
        "lote_id",
        "page",
        "limit",
        "codigo",
        "linha",
    }
    response_schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema["$ref"].endswith("/RazaoWarningListResponse")
    components = client.get("/openapi.json").json()["components"]["schemas"]
    assert components["RazaoWarningListResponse"]["properties"]["source"][
        "enum"
    ] == ["normalized", "legacy"]
