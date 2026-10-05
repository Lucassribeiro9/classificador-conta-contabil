"""Contrato de leitura do plano de contas no contexto da empresa."""

from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from pwdlib import PasswordHash

from core.config import settings
from core.models import (
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    Usuario,
    UsuarioEmpresaPermissao,
)
from tests.conftest import TestingSessionLocal


def _empresa(numero: int) -> Empresa:
    return Empresa(
        nome_empresa=f"Empresa {numero}",
        api_key=f"chave-{numero}",
        cnpj_cpf=f"{numero:014d}",
        cod_dominio=numero,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Ana Contadora",
        login="ana.empresa",
        email="ana.empresa@example.com",
        senha_hash=PasswordHash.recommended().hash("senha-sintetica"),
        papel="contador",
        is_active=True,
    )


def _headers(usuario_id: int) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario_id),
            "role": "contador",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def test_mesmo_codigo_retorna_identidades_e_atributos_da_empresa(client):
    from core.models import ContaContabilEmpresa

    with TestingSessionLocal() as session:
        primeira, segunda = _empresa(1), _empresa(2)
        usuario = _usuario()
        session.add_all([primeira, segunda, usuario])
        session.flush()
        legado = ContaContabil(
            codigo=10046, classificacao="0.1", nome="Nome global",
            tipo="A", grau=2,
        )
        session.add(legado)
        session.add_all(
            [
                UsuarioEmpresaPermissao(
                    usuario_id=usuario.id, empresa_id=primeira.id, permissao="leitura"
                ),
                UsuarioEmpresaPermissao(
                    usuario_id=usuario.id, empresa_id=segunda.id, permissao="leitura"
                ),
                EmpresaContaContabil(
                    empresa_id=primeira.id, conta_codigo=legado.codigo,
                    quantidade_lancamentos=1, ultima_utilizacao=date(2026, 1, 1),
                ),
                ContaContabilEmpresa(
                    empresa_id=primeira.id, codigo=10046, classificacao="1.1",
                    nome="Banco A", tipo="A", grau=2,
                ),
                ContaContabilEmpresa(
                    empresa_id=segunda.id, codigo=10046, classificacao="2.1",
                    nome="Despesa B", tipo="A", grau=2,
                ),
            ]
        )
        session.commit()
        primeira_id, segunda_id, usuario_id = primeira.id, segunda.id, usuario.id

    primeira_resposta = client.get(
        f"/api/v1/empresas/{primeira_id}/plano-contas/10046",
        headers=_headers(usuario_id),
    )
    segunda_resposta = client.get(
        f"/api/v1/empresas/{segunda_id}/plano-contas/10046",
        headers=_headers(usuario_id),
    )

    assert primeira_resposta.status_code == segunda_resposta.status_code == 200
    assert primeira_resposta.json()["nome"] == "Banco A"
    assert segunda_resposta.json()["nome"] == "Despesa B"
    assert primeira_resposta.json()["origem"] == "empresa"
    assert primeira_resposta.json()["id"] != segunda_resposta.json()["id"]
    assert primeira_resposta.json()["empresa_id"] == primeira_id
    assert segunda_resposta.json()["empresa_id"] == segunda_id


def test_resolucao_sem_contexto_de_empresa_falha_fechada(client):
    from core.conta_contabil_empresa import resolver_conta_contabil

    with TestingSessionLocal() as session:
        with pytest.raises(ValueError, match="empresa_id obrigatorio"):
            resolver_conta_contabil(session, empresa_id=None, codigo=10046)


def test_leitura_legada_exige_vinculo_da_empresa(client):
    with TestingSessionLocal() as session:
        empresa, usuario = _empresa(3), _usuario()
        legado = ContaContabil(
            codigo=10046, classificacao="1.1", nome="Legado", tipo="A", grau=2
        )
        sem_vinculo = ContaContabil(
            codigo=20001, classificacao="2.1", nome="Sem vinculo", tipo="A", grau=2
        )
        session.add_all([empresa, usuario, legado, sem_vinculo])
        session.flush()
        session.add_all(
            [
                UsuarioEmpresaPermissao(
                    usuario_id=usuario.id, empresa_id=empresa.id, permissao="leitura"
                ),
                EmpresaContaContabil(
                    empresa_id=empresa.id, conta_codigo=legado.codigo,
                    quantidade_lancamentos=1, ultima_utilizacao=date(2026, 1, 1),
                ),
            ]
        )
        session.commit()
        empresa_id, usuario_id, legado_id = empresa.id, usuario.id, legado.id

    resposta = client.get(
        f"/api/v1/empresas/{empresa_id}/plano-contas/10046",
        headers=_headers(usuario_id),
    )
    ausente = client.get(
        f"/api/v1/empresas/{empresa_id}/plano-contas/20001",
        headers=_headers(usuario_id),
    )

    assert resposta.status_code == 200
    assert resposta.json()["origem"] == "legado"
    assert resposta.json()["id"] is None
    assert resposta.json()["legacy_id"] == legado_id
    assert ausente.status_code == 404


def test_conta_de_outra_empresa_nao_e_legivel_sem_permissao(client):
    from core.models import ContaContabilEmpresa

    with TestingSessionLocal() as session:
        autorizada, privada, usuario = _empresa(4), _empresa(5), _usuario()
        session.add_all([autorizada, privada, usuario])
        session.flush()
        session.add_all(
            [
                UsuarioEmpresaPermissao(
                    usuario_id=usuario.id, empresa_id=autorizada.id,
                    permissao="leitura",
                ),
                ContaContabilEmpresa(
                    empresa_id=privada.id, codigo=10046, classificacao="2.1",
                    nome="Conta privada", tipo="A", grau=2,
                ),
            ]
        )
        session.commit()
        privada_id, usuario_id = privada.id, usuario.id

    resposta = client.get(
        f"/api/v1/empresas/{privada_id}/plano-contas/10046",
        headers=_headers(usuario_id),
    )
    assert resposta.status_code == 403
    assert "Conta privada" not in resposta.text
