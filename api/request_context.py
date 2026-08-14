import re
from contextvars import ContextVar
from uuid import uuid4


REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_current_request_id: ContextVar[str | None] = ContextVar(
    "current_request_id",
    default=None,
)


def get_current_request_id() -> str | None:
    """Retorna o request id associado a requisicao HTTP atual."""
    return _current_request_id.get()


def resolve_request_id(raw_request_id: str | None) -> str:
    """Preserva request ids seguros recebidos ou gera um UUID4 novo."""
    if raw_request_id and _REQUEST_ID_PATTERN.fullmatch(raw_request_id):
        return raw_request_id
    return str(uuid4())


def set_current_request_id(request_id: str):
    """Associa o request id ao contexto assíncrono atual."""
    return _current_request_id.set(request_id)


def reset_current_request_id(token) -> None:
    """Restaura o contexto anterior de request id."""
    _current_request_id.reset(token)
