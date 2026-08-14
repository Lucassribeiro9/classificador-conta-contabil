from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.request_context import REQUEST_ID_HEADER, get_current_request_id


def error_code_for_status(status_code: int) -> str:
    if status_code in {400, 422}:
        return "validation_error"
    if status_code == 401:
        return "authentication_error"
    if status_code == 403:
        return "authorization_error"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if 400 <= status_code < 500:
        return "business_rule_error"
    return "internal_error"


def current_request_id() -> str:
    return get_current_request_id() or "unavailable"


def error_payload(
    *,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": dict(details or {}),
        "request_id": request_id or current_request_id(),
    }


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> JSONResponse:
    request_id = current_request_id()
    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else None
    return error_response(
        status_code=exc.status_code,
        code=error_code_for_status(exc.status_code),
        message=detail or "Nao foi possivel concluir a requisicao.",
    )


def _format_validation_field(location: tuple[Any, ...] | list[Any]) -> str:
    return ".".join(str(part) for part in location)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": _format_validation_field(error.get("loc", [])),
            "message": str(error.get("msg", "Valor invalido")),
        }
        for error in exc.errors()
    ]
    return error_response(
        status_code=422,
        code="validation_error",
        message="Dados invalidos enviados para a API.",
        details={"errors": errors},
    )


async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return error_response(
        status_code=500,
        code="internal_error",
        message="Erro interno inesperado.",
    )
