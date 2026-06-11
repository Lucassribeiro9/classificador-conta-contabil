import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.dependencies import require_company_access
from core.database import Base
from core.models import Empresa, Usuario, UsuarioEmpresaPermissao


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _empresa(**overrides) -> Empresa:
    data = {
        "nome_empresa": "Empresa Auth LTDA",
        "cnpj_cpf": "11222333000144",
        "api_key": "api-key-auth",
        "cod_dominio": 6201,
    }
    data.update(overrides)
    return Empresa(**data)


def _usuario(**overrides) -> Usuario:
    data = {
        "nome": "Ana Contadora",
        "login": "ana.contadora",
        "email": "ana.contadora@example.com",
        "senha_hash": "$argon2id$v=19$hash-de-teste",
        "papel": "contador",
    }
    data.update(overrides)
    return Usuario(**data)


def _grant(usuario: Usuario, empresa: Empresa, permissao: str) -> None:
    usuario.permissoes_empresas.append(
        UsuarioEmpresaPermissao(empresa=empresa, permissao=permissao)
    )


@pytest.mark.parametrize("permissao", ["leitura", "operacao", "admin_empresa"])
def test_company_access_allows_user_with_exact_required_permission(session, permissao):
    empresa = _empresa()
    usuario = _usuario()
    _grant(usuario, empresa, permissao)
    session.add(usuario)
    session.commit()

    dependency = require_company_access(permissao)

    allowed_empresa = dependency(
        company_id=empresa.id,
        current_user=usuario,
        db=session,
    )

    assert allowed_empresa.id == empresa.id


def test_company_access_allows_higher_permission_for_lower_requirement(session):
    empresa = _empresa()
    usuario = _usuario()
    _grant(usuario, empresa, "admin_empresa")
    session.add(usuario)
    session.commit()

    dependency = require_company_access("operacao")

    allowed_empresa = dependency(
        company_id=empresa.id,
        current_user=usuario,
        db=session,
    )

    assert allowed_empresa.id == empresa.id


def test_company_access_rejects_user_without_company_link(session):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario])
    session.commit()

    dependency = require_company_access("leitura")

    with pytest.raises(HTTPException) as exc_info:
        dependency(company_id=empresa.id, current_user=usuario, db=session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Acesso negado"


def test_company_access_rejects_user_with_insufficient_permission(session):
    empresa = _empresa()
    usuario = _usuario()
    _grant(usuario, empresa, "leitura")
    session.add(usuario)
    session.commit()

    dependency = require_company_access("operacao")

    with pytest.raises(HTTPException) as exc_info:
        dependency(company_id=empresa.id, current_user=usuario, db=session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Permissão insuficiente"


def test_company_access_allows_global_admin_without_company_link(session):
    empresa = _empresa()
    usuario = _usuario(papel="admin")
    session.add_all([empresa, usuario])
    session.commit()

    dependency = require_company_access("admin_empresa")

    allowed_empresa = dependency(
        company_id=empresa.id,
        current_user=usuario,
        db=session,
    )

    assert allowed_empresa.id == empresa.id


def test_company_access_rejects_missing_company(session):
    usuario = _usuario(papel="admin")
    session.add(usuario)
    session.commit()

    dependency = require_company_access("leitura")

    with pytest.raises(HTTPException) as exc_info:
        dependency(company_id=999, current_user=usuario, db=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Empresa não encontrada"
