from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.routes import (
    audit,
    auth,
    classification,
    companies,
    feedback,
    movimentos_operacionais,
    notificacoes,
    plano_contas,
    razao,
    transactions,
    users,
)
from core.audit import begin_audit_request_context, end_audit_request_context
from api.error_handlers import (
    error_response,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from api.request_context import (
    REQUEST_ID_HEADER,
    reset_current_request_id,
    resolve_request_id,
    set_current_request_id,
)


app = FastAPI(title="Classificador contábil")
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)


@app.middleware("http")
async def request_context_middleware(request, call_next):
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request_id_token = set_current_request_id(request_id)
    begin_audit_request_context()
    try:
        response = await call_next(request)
    except Exception:
        response = error_response(
            status_code=500,
            code="internal_error",
            message="Erro interno inesperado.",
        )
    finally:
        end_audit_request_context()
        reset_current_request_id(request_id_token)

    response.headers[REQUEST_ID_HEADER] = request_id
    return response


# Checando se está tudo certo
@app.get("/health", tags=["Sistema"])
def health_check(db: Session = Depends(get_db)):
    # Verifica se API e banco estão operacionais
    try:
        # Executa query de checagem
        db.execute(text("SELECT 1"))
        db_status = "online"

    except Exception as e:
        db_status = f"offline. Erro: {str(e)}"
    return {
        "status": "online" if db_status == "online" else "offline",
        "database": db_status,
        "api_version": "v1",
        "env": "desenvolvimento",
    }


# Rotas
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(audit.router, prefix="/api/v1", tags=["Auditoria"])
app.include_router(companies.router, prefix="/api/v1", tags=["Empresas"])
app.include_router(transactions.router, prefix="/api/v1", tags=["Transações"])
app.include_router(classification.router, prefix="/api/v1", tags=["Classificação"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(users.router, prefix="/api/v1", tags=["Usuários"])
app.include_router(
    plano_contas.admin_router,
    prefix="/api/v1",
    tags=["Plano de Contas"],
)
app.include_router(
    plano_contas.catalog_router,
    prefix="/api/v1",
    tags=["Plano de Contas"],
)
app.include_router(razao.router, prefix="/api/v1", tags=["Razão"])
app.include_router(razao.admin_router, prefix="/api/v1", tags=["Razão"])
app.include_router(
    movimentos_operacionais.router,
    prefix="/api/v1",
    tags=["Movimentos Operacionais"],
)
app.include_router(
    notificacoes.router, prefix="/api/v1", tags=["Agente-Notificacoes"]
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version="0.1.0",
        routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components["PublicErrorEnvelope"] = {
        "type": "object",
        "required": ["code", "message", "details", "request_id"],
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "details": {"type": "object", "additionalProperties": True},
            "request_id": {"type": "string"},
        },
    }

    error_response_schema = {
        "description": "Erro publico padronizado",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/PublicErrorEnvelope"}
            }
        },
    }
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            for status_code in ("400", "401", "403", "404", "409", "422", "500"):
                responses.setdefault(status_code, error_response_schema)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def read_root():
    return {"message": "API de Classificação de Contas Contábeis"}
