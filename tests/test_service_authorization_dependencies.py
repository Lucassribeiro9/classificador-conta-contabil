from __future__ import annotations

import asyncio

import httpx
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import get_db, require_service_company_scope
from core.config import settings
from core.database import Base
from core.models import (
    Empresa,
    IdentidadeServico,
    IdentidadeServicoEmpresa,
    IdentidadeServicoEscopo,
)
from core.service_credentials import emitir_credencial_servico


def _make_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = FastAPI()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    def _payload(context):
        return {
            "empresa_id": context.empresa.id,
            "identidade_servico_id": context.identidade.id,
            "credential_fingerprint": context.credential_fingerprint,
        }

    @app.get("/empresas/{company_id}/download")
    def download(context=Depends(require_service_company_scope("movimentos:download"))):
        return _payload(context)

    @app.post("/empresas/{company_id}/feedback")
    def feedback(context=Depends(require_service_company_scope("movimentos:feedback"))):
        return _payload(context)

    class Client:
        def request(self, method: str, url: str, **kwargs):
            async def send_request():
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                ) as client:
                    return await client.request(method, url, **kwargs)

            return asyncio.run(send_request())

        def get(self, url: str, **kwargs):
            return self.request("GET", url, **kwargs)

    return Client(), TestingSession, engine


def _empresa(codigo: int) -> Empresa:
    return Empresa(
        nome_empresa=f"Empresa {codigo}",
        cnpj_cpf=f"12345678{codigo:06d}"[-14:],
        api_key=f"api-key-{codigo}",
        cod_dominio=codigo,
    )


def _criar_identidade_autorizada(
    db, empresa: Empresa, *, escopo: str = "movimentos:download"
):
    identidade = IdentidadeServico(
        identifier=f"n8n-{empresa.cod_dominio}-{escopo.split(':')[-1]}",
        nome="n8n Integracao",
        credential_hash="pendente",
        credential_fingerprint="pendente",
        status="ativa",
        empresas=[IdentidadeServicoEmpresa(empresa=empresa)],
        escopos=[IdentidadeServicoEscopo(escopo=escopo)],
    )
    db.add(identidade)
    db.commit()
    credencial = emitir_credencial_servico(db, identidade_id=identidade.id)
    db.commit()
    return identidade, credencial


def test_service_credential_com_escopo_e_empresa_permitidos_acessa_recurso():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa = _empresa(9001)
        db.add(empresa)
        db.commit()
        identidade, credencial = _criar_identidade_autorizada(db, empresa)
        empresa_id = empresa.id
        identidade_id = identidade.id
        db.close()

        response = client.get(
            f"/empresas/{empresa_id}/download",
            headers={"X-Service-Credential": credencial.secret},
        )

        assert response.status_code == 200
        assert response.json() == {
            "empresa_id": empresa_id,
            "identidade_servico_id": identidade_id,
            "credential_fingerprint": credencial.fingerprint,
        }
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_service_credential_ausente_ou_invalida_retorna_401():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, _TestingSession, engine = _make_client()
    try:
        sem_header = client.get("/empresas/1/download")
        invalida = client.get(
            "/empresas/1/download",
            headers={"X-Service-Credential": "svc_invalida"},
        )

        assert sem_header.status_code == 401
        assert invalida.status_code == 401
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_service_credential_sem_escopo_retorna_403():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa = _empresa(9002)
        db.add(empresa)
        db.commit()
        _identidade, credencial = _criar_identidade_autorizada(
            db,
            empresa,
            escopo="movimentos:feedback",
        )
        empresa_id = empresa.id
        db.close()

        response = client.get(
            f"/empresas/{empresa_id}/download",
            headers={"X-Service-Credential": credencial.secret},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Escopo de serviço insuficiente"
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_service_credential_de_outra_empresa_retorna_403():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa_autorizada = _empresa(9003)
        empresa_bloqueada = _empresa(9004)
        db.add_all([empresa_autorizada, empresa_bloqueada])
        db.commit()
        _identidade, credencial = _criar_identidade_autorizada(db, empresa_autorizada)
        empresa_bloqueada_id = empresa_bloqueada.id
        db.close()

        response = client.get(
            f"/empresas/{empresa_bloqueada_id}/download",
            headers={"X-Service-Credential": credencial.secret},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Acesso negado para empresa"
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_service_credential_revogada_ou_inativa_retorna_403():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa = _empresa(9005)
        db.add(empresa)
        db.commit()
        identidade, credencial = _criar_identidade_autorizada(db, empresa)
        empresa_id = empresa.id
        identidade_id = identidade.id
        identidade.status = "revogada"
        db.commit()
        db.close()

        revogada = client.get(
            f"/empresas/{empresa_id}/download",
            headers={"X-Service-Credential": credencial.secret},
        )

        db = TestingSession()
        identidade = db.get(IdentidadeServico, identidade_id)
        identidade.status = "inativa"
        db.commit()
        db.close()
        inativa = client.get(
            f"/empresas/{empresa_id}/download",
            headers={"X-Service-Credential": credencial.secret},
        )

        assert revogada.status_code == 403
        assert inativa.status_code == 403
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_jwt_e_headers_legados_nao_autorizam_dependencia_de_servico():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, _TestingSession, engine = _make_client()
    try:
        somente_jwt = client.get(
            "/empresas/1/download",
            headers={"Authorization": "Bearer token-humano"},
        )
        somente_api_key = client.get(
            "/empresas/1/download",
            headers={"X-API-Key": "api-key-legada"},
        )
        somente_admin = client.get(
            "/empresas/1/download",
            headers={"X-Admin-Token": "admin-legado"},
        )

        assert somente_jwt.status_code == 401
        assert somente_api_key.status_code == 401
        assert somente_admin.status_code == 401
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_service_credential_com_escopo_feedback_acessa_recurso_feedback():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa = _empresa(9006)
        db.add(empresa)
        db.commit()
        identidade, credencial = _criar_identidade_autorizada(
            db,
            empresa,
            escopo="movimentos:feedback",
        )
        empresa_id = empresa.id
        identidade_id = identidade.id
        db.close()

        response = client.request(
            "POST",
            f"/empresas/{empresa_id}/feedback",
            headers={"X-Service-Credential": credencial.secret},
        )

        assert response.status_code == 200
        assert response.json() == {
            "empresa_id": empresa_id,
            "identidade_servico_id": identidade_id,
            "credential_fingerprint": credencial.fingerprint,
        }
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_headers_legados_sao_ignorados_quando_credencial_de_servico_e_valida():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    client, TestingSession, engine = _make_client()
    try:
        db = TestingSession()
        empresa = _empresa(9007)
        db.add(empresa)
        db.commit()
        _identidade, credencial = _criar_identidade_autorizada(db, empresa)
        empresa_id = empresa.id
        db.close()

        response = client.get(
            f"/empresas/{empresa_id}/download",
            headers={
                "X-Service-Credential": credencial.secret,
                "X-API-Key": "api-key-legada-incorreta",
                "X-Admin-Token": "admin-token-legado-incorreto",
            },
        )

        assert response.status_code == 200
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
