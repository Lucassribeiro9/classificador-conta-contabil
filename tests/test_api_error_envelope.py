from uuid import UUID

from api.main import app


def test_response_includes_generated_request_id_header(client):
    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 4


def test_response_preserves_safe_request_id_header(client):
    response = client.get("/health", headers={"X-Request-ID": "agent-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "agent-test-123"


def test_response_replaces_unsafe_request_id_header(client):
    response = client.get("/health", headers={"X-Request-ID": "valor\ninterno"})

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert request_id != "valor\ninterno"
    assert UUID(request_id).version == 4


def test_http_exception_uses_public_error_envelope(client):
    response = client.get("/api/v1/companies")

    assert response.status_code == 401
    request_id = response.headers["X-Request-ID"]
    assert response.json() == {
        "code": "authentication_error",
        "message": "Admin token ausente",
        "details": {},
        "request_id": request_id,
    }
    assert "detail" not in response.json()


def test_validation_error_uses_simplified_details(client):
    response = client.post("/api/v1/auth/login", json={"login": "operador.demo"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert payload["message"] == "Dados invalidos enviados para a API."
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert "detail" not in payload
    assert payload["details"] == {
        "errors": [
            {"field": "body.senha", "message": "Field required"},
        ]
    }


def test_unexpected_error_uses_safe_public_envelope(client):
    route_path = "/__tests__/unexpected-error-envelope"
    if not any(route.path == route_path for route in app.routes):
        @app.get(route_path)
        def _raise_unexpected_error():
            raise RuntimeError("valor interno em excecao bruta")

    response = client.get(route_path)

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        "code": "internal_error",
        "message": "Erro interno inesperado.",
        "details": {},
        "request_id": response.headers["X-Request-ID"],
    }
    assert "valor interno" not in response.text
    assert "detail" not in payload
