"""
Configuração compartilhada para os testes da API.
Define fixtures reutilizáveis como cliente de teste e banco de dados em memória.
"""

import asyncio

import fastapi.dependencies.utils
import fastapi.routing
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db
from api.main import app
from core.database import Base
from core.config import settings


async def _run_sync_inline(func, *args, **kwargs):
    return func(*args, **kwargs)


fastapi.routing.run_in_threadpool = _run_sync_inline
fastapi.dependencies.utils.run_in_threadpool = _run_sync_inline


# Cria banco de dados SQLite em memória para testes
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class ASGITestClient:
    """Cliente síncrono de teste usando transporte ASGI direto.

    Evita o `TestClient`, que trava neste ambiente ao executar requisições via
    portal/threadpool, mantendo a mesma ergonomia usada pelos testes atuais.
    """

    def __init__(self, app):
        self.app = app

    def request(self, method: str, url: str, **kwargs):
        async def send_request():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send_request())

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture(scope="function")
def setup_db():
    """Cria schema limpo para cada teste."""
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(setup_db):
    """Cliente de teste FastAPI com banco de dados isolado."""

    async def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield ASGITestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def admin_token():
    """Configura os testes do token de admin para as sessões requeridas.
    Gera um token de admin para autenticação nos testes."""
    return "test-admin-token"
@pytest.fixture(scope="function", autouse=True)
def override_admin_token(admin_token):
    """Sobrescreve a dependência de token de admin para usar o token de teste."""
    previous = settings.ADMIN_TOKEN
    settings.ADMIN_TOKEN = admin_token
    try:
        yield
    finally:
        settings.ADMIN_TOKEN = previous
@pytest.fixture
def admin_headers(admin_token):
    """Headers de autenticação para admin."""
    return {"X-Admin-Token": admin_token}
@pytest.fixture
def empresa_data():
    """Dados padrão para criar uma empresa de teste."""
    return {
        "nome_empresa": "Empresa Teste LTDA",
        "cnpj_cpf": "12345678000199",
        "cod_dominio": 1001,
    }


@pytest.fixture
def empresa_criada(client, empresa_data, admin_headers):
    """Cria e retorna uma empresa para uso nos testes."""
    response = client.post("/api/v1/companies", json=empresa_data, headers=admin_headers)
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def transacao_data():
    """Dados padrão para criar transações de teste."""
    return [
        {
            "data": "2026-01-15",
            "cod_banco": 341,
            "historico": "Pagamento fornecedor material escritório",
            "valor": -500.00,
            "conta_contabil": None,
            "empresa_id": 1,
        },
        {
            "data": "2026-01-16",
            "cod_banco": 341,
            "historico": "Recebimento cliente serviços consultoria",
            "valor": 2500.00,
            "conta_contabil": None,
            "empresa_id": 1,
        },
    ]
