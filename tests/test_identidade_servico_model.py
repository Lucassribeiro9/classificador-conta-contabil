from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    Empresa,
    IdentidadeServico,
    IdentidadeServicoEmpresa,
    IdentidadeServicoEscopo,
    Usuario,
)


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    return db, engine


def _empresa(codigo: int = 9001) -> Empresa:
    return Empresa(
        nome_empresa=f"Empresa Integracao {codigo} LTDA",
        cnpj_cpf=f"11222333{codigo:06d}"[-14:],
        api_key=f"api-key-integracao-{codigo}",
        cod_dominio=codigo,
    )


def test_identidade_servico_e_entidade_propria_com_empresas_e_escopos_explicitos():
    db, engine = _session()
    try:
        empresa = _empresa()
        identidade = IdentidadeServico(
            identifier="n8n-contabilidade",
            nome="n8n Contabilidade",
            credential_hash="sha256:hash-da-credencial",
            credential_fingerprint="fp_1234567890ab",
            status="ativa",
            empresas=[IdentidadeServicoEmpresa(empresa=empresa)],
            escopos=[
                IdentidadeServicoEscopo(escopo="empresas:read"),
                IdentidadeServicoEscopo(escopo="movimentos:download"),
            ],
        )

        db.add(identidade)
        db.commit()

        saved = db.query(IdentidadeServico).one()
        assert saved.id is not None
        assert not isinstance(saved, Usuario)
        assert saved.usuario_id is None if hasattr(saved, "usuario_id") else True
        assert [empresa.empresa.cod_dominio for empresa in saved.empresas] == [9001]
        assert {escopo.escopo for escopo in saved.escopos} == {
            "empresas:read",
            "movimentos:download",
        }
        assert saved.credential_hash == "sha256:hash-da-credencial"
        assert saved.credential_fingerprint == "fp_1234567890ab"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_identidade_servico_restringe_status_escopos_e_unicidade():
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-unico",
            nome="n8n Unico",
            credential_hash="sha256:hash-1",
            credential_fingerprint="fp_unico_1",
            status="ativa",
            escopos=[IdentidadeServicoEscopo(escopo="ml:classificar")],
        )
        db.add(identidade)
        db.commit()

        duplicada = IdentidadeServico(
            identifier="n8n-unico",
            nome="n8n Duplicado",
            credential_hash="sha256:hash-2",
            credential_fingerprint="fp_unico_2",
            status="ativa",
        )
        db.add(duplicada)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        fingerprint_duplicado = IdentidadeServico(
            identifier="n8n-fingerprint",
            nome="n8n Fingerprint",
            credential_hash="sha256:hash-3",
            credential_fingerprint="fp_unico_1",
            status="ativa",
        )
        db.add(fingerprint_duplicado)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        status_invalido = IdentidadeServico(
            identifier="n8n-status",
            nome="n8n Status",
            credential_hash="sha256:hash-4",
            credential_fingerprint="fp_status",
            status="global",
        )
        db.add(status_invalido)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        escopo_invalido = IdentidadeServico(
            identifier="n8n-escopo",
            nome="n8n Escopo",
            credential_hash="sha256:hash-5",
            credential_fingerprint="fp_escopo",
            status="ativa",
            escopos=[IdentidadeServicoEscopo(escopo="admin:global")],
        )
        db.add(escopo_invalido)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_identidade_servico_nao_tem_coluna_de_segredo_puro():
    forbidden = {"token", "secret", "segredo", "api_key", "credential"}
    columns = set(IdentidadeServico.__table__.c.keys())

    assert "credential_hash" in columns
    assert "credential_fingerprint" in columns
    assert forbidden.isdisjoint(columns)


def test_identidade_servico_possui_datas_e_responsaveis_estruturais():
    columns = set(IdentidadeServico.__table__.c.keys())

    assert {
        "created_at",
        "updated_at",
        "revoked_at",
        "last_used_at",
        "expires_at",
        "created_by_user_id",
        "revoked_by_user_id",
    } <= columns


def test_migration_cria_tabelas_de_identidade_servico():
    migration_files = list(
        Path("alembic/versions").glob("*_add_service_identity_models.py")
    )
    assert len(migration_files) == 1
    migration = migration_files[0].read_text()

    for table_name in (
        "identidades_servico",
        "identidade_servico_empresas",
        "identidade_servico_escopos",
    ):
        assert f'"{table_name}"' in migration

    assert "ck_identidades_servico_status" in migration
    assert "ck_identidade_servico_escopos_escopo" in migration
    assert "uq_identidade_servico_empresas_identidade_empresa" in migration
    assert "uq_identidade_servico_escopos_identidade_escopo" in migration
    assert "credential_hash" in migration
    assert "credential_fingerprint" in migration
    assert "api_key" not in migration
    assert "secret" not in migration
    assert "token" not in migration
