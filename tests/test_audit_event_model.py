from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import AuditEvent, Empresa, Usuario


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
        nome_empresa="Empresa Audit LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-audit",
        cod_dominio=7301,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Ana Auditora",
        login="ana.auditora",
        email="ana.auditora@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="admin",
    )


def test_audit_event_can_be_persisted_with_flexible_metadata(session):
    empresa = _empresa()
    usuario = _usuario()
    event = AuditEvent(
        event_type="ledger_import.completed",
        usuario=usuario,
        empresa=empresa,
        resource_id="22",
        metadata_json={
            "linhas_importadas": 583,
            "warnings": [{"linha": 12, "motivo": "conta ausente"}],
        },
    )

    session.add(event)
    session.commit()

    saved = session.query(AuditEvent).one()
    assert saved.id is not None
    assert saved.event_type == "ledger_import.completed"
    assert saved.usuario.login == "ana.auditora"
    assert saved.empresa.cnpj_cpf == "11222333000144"
    assert saved.resource_id == "22"
    assert saved.metadata_json["linhas_importadas"] == 583
    assert saved.metadata_json["warnings"][0]["linha"] == 12
    assert isinstance(saved.timestamp, datetime)
    assert "metadata" in AuditEvent.__table__.c


def test_audit_event_allows_background_event_without_user_or_company(session):
    event = AuditEvent(
        event_type="system.backup.completed",
        resource_id=None,
        metadata_json={"duration_seconds": 7.4},
    )

    session.add(event)
    session.commit()

    saved = session.query(AuditEvent).one()
    assert saved.user_id is None
    assert saved.empresa_id is None
    assert saved.resource_id is None
    assert saved.metadata_json == {"duration_seconds": 7.4}
