import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import settings
from core.database import Base
from core.models import AuditEvent, IdentidadeServico
from core.service_credentials import (
    autenticar_credencial_servico,
    emitir_credencial_servico,
    revogar_credencial_servico,
    rotacionar_credencial_servico,
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


def test_emitir_credencial_exibe_segredo_apenas_no_retorno_e_persiste_hash_fingerprint():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-contabilidade",
            nome="n8n Contabilidade",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
        )
        db.add(identidade)
        db.commit()

        credencial = emitir_credencial_servico(
            db,
            identidade_id=identidade.id,
            actor_user_id=10,
        )
        db.commit()

        saved = db.get(IdentidadeServico, identidade.id)
        events = db.query(AuditEvent).all()

        assert credencial.secret.startswith("svc_n8n-contabilidade_")
        assert credencial.fingerprint == saved.credential_fingerprint
        assert saved.credential_hash != credencial.secret
        assert saved.credential_fingerprint not in {"", "pendente"}
        assert saved.credential_hash not in {"", "pendente"}
        assert credencial.secret not in str(saved.__dict__)
        assert len(events) == 1
        assert events[0].event_type == "service_credential.issued"
        assert events[0].user_id == 10
        assert events[0].resource_id == str(identidade.id)
        assert credencial.secret not in str(events[0].metadata_json)
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_autenticar_credencial_retorna_identidade_ativa_e_bloqueia_invalidas():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-auth",
            nome="n8n Auth",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
        )
        db.add(identidade)
        db.commit()
        credencial = emitir_credencial_servico(db, identidade_id=identidade.id)
        db.commit()

        autenticada = autenticar_credencial_servico(db, credencial.secret)
        assert autenticada is not None
        assert autenticada.id == identidade.id
        assert autenticada.last_used_at is not None

        assert autenticar_credencial_servico(db, "svc_n8n-auth_invalida") is None

        identidade.status = "inativa"
        db.commit()
        assert autenticar_credencial_servico(db, credencial.secret) is None
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_rotacionar_credencial_invalida_segredo_anterior_e_audita_sem_segredo():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-rotate",
            nome="n8n Rotate",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
        )
        db.add(identidade)
        db.commit()
        antiga = emitir_credencial_servico(db, identidade_id=identidade.id)
        db.commit()

        nova = rotacionar_credencial_servico(
            db,
            identidade_id=identidade.id,
            actor_user_id=11,
        )
        db.commit()

        saved = db.get(IdentidadeServico, identidade.id)
        events = db.query(AuditEvent).order_by(AuditEvent.id).all()

        assert nova.secret != antiga.secret
        assert saved.credential_fingerprint == nova.fingerprint
        assert autenticar_credencial_servico(db, antiga.secret) is None
        assert autenticar_credencial_servico(db, nova.secret).id == identidade.id
        assert events[-1].event_type == "service_credential.rotated"
        assert events[-1].user_id == 11
        assert antiga.secret not in str(events[-1].metadata_json)
        assert nova.secret not in str(events[-1].metadata_json)
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_revogar_credencial_bloqueia_novos_usos_e_audita_sem_segredo():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = "segredo-hmac-de-teste"
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-revoke",
            nome="n8n Revoke",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
        )
        db.add(identidade)
        db.commit()
        credencial = emitir_credencial_servico(db, identidade_id=identidade.id)
        db.commit()

        revogada = revogar_credencial_servico(
            db,
            identidade_id=identidade.id,
            actor_user_id=12,
        )
        db.commit()

        events = db.query(AuditEvent).order_by(AuditEvent.id).all()
        assert revogada.status == "revogada"
        assert revogada.revoked_at is not None
        assert revogada.revoked_by_user_id == 12
        assert autenticar_credencial_servico(db, credencial.secret) is None
        assert events[-1].event_type == "service_credential.revoked"
        assert events[-1].user_id == 12
        assert credencial.secret not in str(events[-1].metadata_json)
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_emitir_credencial_exige_service_credential_secret_configurado():
    previous_secret = settings.SERVICE_CREDENTIAL_SECRET
    settings.SERVICE_CREDENTIAL_SECRET = ""
    db, engine = _session()
    try:
        identidade = IdentidadeServico(
            identifier="n8n-sem-segredo",
            nome="n8n Sem Segredo",
            credential_hash="pendente",
            credential_fingerprint="pendente",
            status="ativa",
        )
        db.add(identidade)
        db.commit()

        with pytest.raises(RuntimeError, match="SERVICE_CREDENTIAL_SECRET"):
            emitir_credencial_servico(db, identidade_id=identidade.id)
    finally:
        settings.SERVICE_CREDENTIAL_SECRET = previous_secret
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
