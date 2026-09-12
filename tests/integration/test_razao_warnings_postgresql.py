"""Contrato HTTP de warnings do Razão sobre PostgreSQL real."""

import asyncio
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import fastapi.dependencies.utils
import fastapi.routing
import httpx
import jwt
import pytest
from sqlalchemy import create_engine, delete, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from api.dependencies import get_db
from api.main import app
from core.config import settings
from core.models import (
    Empresa,
    LoteImportacaoRazao,
    Usuario,
    UsuarioEmpresaPermissao,
    WarningImportacaoRazao,
)

pytestmark = pytest.mark.integration_postgres


async def _run_sync_inline(func, *args, **kwargs):
    return func(*args, **kwargs)


fastapi.routing.run_in_threadpool = _run_sync_inline
fastapi.dependencies.utils.run_in_threadpool = _run_sync_inline


class ASGITestClient:
    def __init__(self, application):
        self.application = application

    def get(self, url, **kwargs):
        async def send_request():
            transport = httpx.ASGITransport(app=self.application)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, **kwargs)

        return asyncio.run(send_request())


def _auth_headers(usuario):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "role": usuario.papel,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_warning_filters_and_stable_pagination_use_postgresql():
    url = os.environ.get("DATABASE_URL", "")
    assert url and make_url(url).get_backend_name() == "postgresql"
    engine = create_engine(url)
    statements = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture_statement(_connection, _cursor, statement, *_args):
        statements.append(statement)

    sessions = sessionmaker(engine)
    suffix = uuid4().hex[:12]
    with sessions.begin() as session:
        empresa = Empresa(
            nome_empresa="Warnings sintéticos",
            api_key=f"warnings-{suffix}",
            cnpj_cpf=str(int(suffix, 16) % 10**14).zfill(14),
            cod_dominio=int(suffix, 16) % 2_000_000_000,
        )
        usuario = Usuario(
            nome="Leitor de warnings",
            login=f"warnings-{suffix}",
            email=f"warnings-{suffix}@example.com",
            senha_hash="synthetic",
            papel="operador",
        )
        session.add_all([empresa, usuario])
        session.flush()
        session.add(
            UsuarioEmpresaPermissao(
                usuario_id=usuario.id,
                empresa_id=empresa.id,
                permissao="leitura",
            )
        )
        lote = LoteImportacaoRazao(
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="synthetic.xlsx",
            file_hash=f"sha256:{suffix}",
            status="completed_with_warnings",
            total_linhas=4,
            linhas_processadas=4,
            total_importadas=4,
            warnings_total=4,
            warnings_metadata={"totals_by_code": {"synthetic": 3, "other": 1}},
        )
        session.add(lote)
        session.flush()
        session.add_all(
            [
                WarningImportacaoRazao(
                    lote_id=lote.id,
                    linha=linha,
                    codigo=codigo,
                    mensagem=f"Aviso sintético {linha}.",
                    detalhes={},
                )
                for linha, codigo in [
                    (1, "synthetic"),
                    (2, "other"),
                    (3, "synthetic"),
                    (4, "synthetic"),
                ]
            ]
        )
        empresa_id = empresa.id
        lote_id = lote.id
        usuario_id = usuario.id
        headers = _auth_headers(usuario)

    def override_get_db():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = ASGITestClient(app).get(
            f"/api/v1/companies/{empresa_id}/razao/lotes/{lote_id}/warnings",
            params={"codigo": "synthetic", "page": 2, "limit": 2},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert response.json()["has_next"] is False
        assert [item["linha"] for item in response.json()["items"]] == [4]
        item_queries = [
            statement
            for statement in statements
            if "FROM warnings_importacao_razao" in statement
            and "count(" not in statement.lower()
        ]
        assert len(item_queries) == 1
        assert "LIMIT" in item_queries[0]
        assert "OFFSET" in item_queries[0]
    finally:
        app.dependency_overrides.pop(get_db, None)
        with sessions.begin() as session:
            session.execute(
                delete(LoteImportacaoRazao).where(
                    LoteImportacaoRazao.empresa_id == empresa_id
                )
            )
            session.execute(delete(Usuario).where(Usuario.id == usuario_id))
            session.execute(delete(Empresa).where(Empresa.id == empresa_id))
        engine.dispose()
