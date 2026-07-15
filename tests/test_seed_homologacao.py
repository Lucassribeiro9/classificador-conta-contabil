import os
import subprocess
import sys
from pathlib import Path

import pytest
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    ContaContabil,
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoMovimentoOperacional,
    LoteImportacaoRazao,
    MovimentoOperacionalImportado,
    Usuario,
    UsuarioEmpresaPermissao,
)
from scripts.seed_homologacao import seed_homologacao


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "homologacao"


@pytest.fixture()
def database_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_seed_cli_refuses_non_hml_environment_before_opening_database(tmp_path):
    database_path = tmp_path / "producao.db"
    env = {
        **os.environ,
        "APP_ENV": "prod",
        "DATABASE_URL": f"sqlite:///{database_path}",
    }

    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_homologacao"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Seed recusado: APP_ENV deve ser hml." in result.stderr
    assert not database_path.exists()


def test_seed_creates_sanitized_company_users_permission_and_imports(database_engine):
    seed_homologacao(
        app_env="hml",
        database_url="sqlite://",
        admin_password="senha-admin-hml",
        operator_password="senha-operador-hml",
        company_api_key="api-key-hml-ficticia",
        fixtures_dir=FIXTURES_DIR,
        engine=database_engine,
    )

    Session = sessionmaker(bind=database_engine)
    with Session() as session:
        empresa = session.query(Empresa).one()
        usuarios = session.query(Usuario).order_by(Usuario.papel).all()
        permissao = session.query(UsuarioEmpresaPermissao).one()

        assert empresa.nome_empresa == "EMPRESA MODELO HOMOLOGACAO LTDA"
        assert empresa.cnpj_cpf == "22333444000155"
        assert empresa.cod_dominio == 7701
        assert [(usuario.login, usuario.papel) for usuario in usuarios] == [
            ("admin.hml", "admin"),
            ("operador.hml", "operador"),
        ]
        assert PasswordHash.recommended().verify(
            "senha-admin-hml", usuarios[0].senha_hash
        )
        assert PasswordHash.recommended().verify(
            "senha-operador-hml", usuarios[1].senha_hash
        )
        assert permissao.usuario_id == usuarios[1].id
        assert permissao.empresa_id == empresa.id
        assert permissao.permissao == "operacao"
        assert session.query(ContaContabil).count() == 13
        assert session.query(LoteImportacaoRazao).count() == 1
        assert session.query(LancamentoRazaoNormalizado).count() == 12
        assert session.query(LoteImportacaoMovimentoOperacional).count() == 1
        assert session.query(MovimentoOperacionalImportado).count() == 5


def test_seed_is_idempotent_for_identity_permissions_and_imports(database_engine):
    seed_args = {
        "app_env": "hml",
        "database_url": "sqlite://",
        "admin_password": "senha-admin-hml",
        "operator_password": "senha-operador-hml",
        "company_api_key": "api-key-hml-ficticia",
        "fixtures_dir": FIXTURES_DIR,
        "engine": database_engine,
    }

    seed_homologacao(**seed_args)
    seed_homologacao(
        **{
            **seed_args,
            "admin_password": "nova-senha-admin",
            "operator_password": "nova-senha-operador",
            "company_api_key": "nova-api-key",
        }
    )

    Session = sessionmaker(bind=database_engine)
    with Session() as session:
        empresa = session.query(Empresa).one()
        usuarios = session.query(Usuario).order_by(Usuario.papel).all()

        assert empresa.api_key == "api-key-hml-ficticia"
        assert PasswordHash.recommended().verify(
            "senha-admin-hml", usuarios[0].senha_hash
        )
        assert PasswordHash.recommended().verify(
            "senha-operador-hml", usuarios[1].senha_hash
        )
        assert session.query(Empresa).count() == 1
        assert session.query(Usuario).count() == 2
        assert session.query(UsuarioEmpresaPermissao).count() == 1
        assert session.query(ContaContabil).count() == 13
        assert session.query(LoteImportacaoRazao).count() == 1
        assert session.query(LancamentoRazaoNormalizado).count() == 12
        assert session.query(LoteImportacaoMovimentoOperacional).count() == 1
        assert session.query(MovimentoOperacionalImportado).count() == 5


def test_seed_cli_requires_runtime_secrets_before_opening_database(tmp_path):
    database_path = tmp_path / "homologacao.db"
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "HML_ADMIN_PASSWORD",
            "HML_OPERATOR_PASSWORD",
            "HML_COMPANY_API_KEY",
        }
    }
    env.update(
        {
            "APP_ENV": "hml",
            "DATABASE_URL": f"sqlite:///{database_path}",
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "scripts.seed_homologacao"],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Variaveis obrigatorias ausentes" in result.stderr
    assert "HML_ADMIN_PASSWORD" in result.stderr
    assert "HML_OPERATOR_PASSWORD" in result.stderr
    assert "HML_COMPANY_API_KEY" in result.stderr
    assert not database_path.exists()
