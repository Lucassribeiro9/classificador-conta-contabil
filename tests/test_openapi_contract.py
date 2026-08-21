"""Contratos documentais do OpenAPI exposto pela API."""

from api.main import app


EXPECTED_TAGS = {
    "Sistema",
    "Auth",
    "Auditoria",
    "Empresas",
    "Transações",
    "Classificação",
    "Feedback",
    "Usuários",
    "Plano de Contas",
    "Razão",
    "Movimentos Operacionais",
    "Agente-Notificacoes",
}

EXPECTED_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/companies",
    "/api/v1/companies/authorized",
    "/api/v1/companies/{company_id}/movimentos-operacionais/import",
    "/api/v1/companies/{company_id}/movimentos-operacionais/lotes",
    "/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada",
    "/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada/feedback",
    "/api/v1/companies/{company_id}/razao/import",
    "/api/v1/companies/{company_id}/razao/lotes",
    "/api/v1/admin/plano-contas/import",
    "/api/v1/plano-contas",
    "/api/v1/companies/{company_id}/ml/status",
    "/api/v1/companies/{company_id}/ml/classification",
    "/api/v1/companies/{company_id}/ml/train",
    "/api/v1/companies/{company_id}/ml/feedback",
    "/api/v1/companies/{company_id}/transactions",
}


def test_openapi_schema_is_generated_and_parseable():
    schema = app.openapi()

    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Classificador contábil"
    assert isinstance(schema["paths"], dict)
    assert schema["paths"]


def test_openapi_contains_main_route_groups_and_paths():
    schema = app.openapi()
    paths = schema["paths"]
    tags = {
        tag
        for path_item in paths.values()
        for operation in path_item.values()
        for tag in operation.get("tags", [])
    }

    assert EXPECTED_TAGS.issubset(tags)
    assert EXPECTED_PATHS.issubset(paths.keys())


def test_openapi_declares_public_error_envelope_schema():
    schema = app.openapi()
    error_schema = schema["components"]["schemas"]["PublicErrorEnvelope"]

    assert set(error_schema["required"]) == {
        "code",
        "message",
        "details",
        "request_id",
    }
    assert error_schema["properties"]["code"]["type"] == "string"
    assert error_schema["properties"]["message"]["type"] == "string"
    assert error_schema["properties"]["details"]["type"] == "object"
    assert error_schema["properties"]["request_id"]["type"] == "string"


def test_openapi_declares_operational_lote_layout_version():
    schema = app.openapi()
    lote_schema = schema["components"]["schemas"]["MovimentoOperacionalLoteResponse"]

    assert "layout_version" in lote_schema["properties"]
    assert lote_schema["properties"]["layout_version"]["type"] == "string"


def test_openapi_declares_operational_movement_balance_fields():
    schema = app.openapi()
    movimento_schema = schema["components"]["schemas"]["MovimentoOperacionalResponse"]
    properties = movimento_schema["properties"]

    assert "saldo_observado_original" in properties
    assert "saldo_observado_decimal" in properties
    assert "saldo_calculado_decimal" in properties
    assert "warnings_saldo" in properties
    assert properties["warnings_saldo"]["items"]["type"] == "string"


def test_roundtrip_endpoints_document_service_credential_header(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    endpoints = [
        (
            "/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada",
            "get",
        ),
        (
            "/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada/feedback",
            "post",
        ),
    ]

    for path, method in endpoints:
        parameters = paths[path][method]["parameters"]
        service_header = [
            parameter
            for parameter in parameters
            if parameter["in"] == "header"
            and parameter["name"] == "X-Service-Credential"
        ]
        operation = paths[path][method]
        assert service_header
        assert service_header[0]["required"] is False
        assert any("HTTPBearer" in security for security in operation.get("security", []))
