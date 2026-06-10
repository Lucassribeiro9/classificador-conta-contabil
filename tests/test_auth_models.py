from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def _empresa() -> Empresa:
    return Empresa(
        nome_empresa="Empresa Auth LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-auth",
        cod_dominio=6201,
    )


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


def test_usuario_interno_can_be_persisted_with_approved_global_role(session):
    usuario = _usuario(papel="admin")

    session.add(usuario)
    session.commit()

    saved = session.query(Usuario).one()
    assert saved.nome == "Ana Contadora"
    assert saved.login == "ana.contadora"
    assert saved.email == "ana.contadora@example.com"
    assert saved.senha_hash.startswith("$argon2id$")
    assert saved.papel == "admin"
    assert saved.is_active is True
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


@pytest.mark.parametrize(
    ("field", "duplicate_value"),
    [
        ("login", "duplicado"),
        ("email", "duplicado@example.com"),
    ],
)
def test_usuario_login_and_email_are_unique(session, field, duplicate_value):
    first = _usuario(login="usuario-1", email="usuario-1@example.com")
    second = _usuario(login="usuario-2", email="usuario-2@example.com")
    setattr(first, field, duplicate_value)
    setattr(second, field, duplicate_value)

    session.add_all([first, second])

    with pytest.raises(IntegrityError):
        session.commit()


def test_usuario_empresa_permission_link_records_approved_permission(session):
    empresa = _empresa()
    usuario = _usuario(papel="operador")
    vinculo = UsuarioEmpresaPermissao(
        usuario=usuario,
        empresa=empresa,
        permissao="operacao",
    )

    session.add(vinculo)
    session.commit()

    saved = session.query(UsuarioEmpresaPermissao).one()
    assert saved.usuario.login == "ana.contadora"
    assert saved.empresa.cnpj_cpf == "11222333000144"
    assert saved.permissao == "operacao"
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


@pytest.mark.parametrize("papel", ["admin", "contador", "operador"])
def test_usuario_accepts_only_approved_global_roles(session, papel):
    session.add(_usuario(papel=papel))

    session.commit()

    assert session.query(Usuario).one().papel == papel


def test_usuario_rejects_unapproved_global_role(session):
    session.add(_usuario(papel="superuser"))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("permissao", ["leitura", "operacao", "admin_empresa"])
def test_usuario_empresa_permission_accepts_only_approved_values(session, permissao):
    session.add(
        UsuarioEmpresaPermissao(
            usuario=_usuario(),
            empresa=_empresa(),
            permissao=permissao,
        )
    )

    session.commit()

    assert session.query(UsuarioEmpresaPermissao).one().permissao == permissao


def test_usuario_empresa_permission_rejects_unapproved_value(session):
    session.add(
        UsuarioEmpresaPermissao(
            usuario=_usuario(),
            empresa=_empresa(),
            permissao="dono",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
