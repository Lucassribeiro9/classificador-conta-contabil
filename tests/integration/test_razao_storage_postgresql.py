"""Coordenação de arquivos com transações e row locks em PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from core.models import Empresa, LoteImportacaoRazao, Usuario
from core.razao_storage import (
    RazaoStorage,
    TemporaryFileBusy,
    TemporaryFileUnavailable,
)

pytestmark = pytest.mark.integration_postgres


@pytest.fixture
def storage_db(tmp_path):
    """Cria somente registros sintéticos e remove-os ao encerrar cada caso."""
    url = os.environ.get("DATABASE_URL", "")
    assert url and make_url(url).get_backend_name() == "postgresql"
    engine = create_engine(url)
    sessions = sessionmaker(engine)
    suffix = uuid4().hex[:12]
    with sessions.begin() as session:
        empresa = Empresa(nome_empresa="Storage sintético", api_key=suffix,
                          cnpj_cpf=str(int(suffix, 16) % 10**14).zfill(14),
                          cod_dominio=int(suffix, 16) % 2_000_000_000)
        usuario = Usuario(nome="Storage", login=suffix, email=f"{suffix}@example.com",
                          senha_hash="synthetic", papel="operador")
        session.add_all([empresa, usuario])
        session.flush()
        ids = empresa.id, usuario.id
    try:
        yield sessions, ids
    finally:
        with sessions.begin() as session:
            session.execute(delete(LoteImportacaoRazao).where(LoteImportacaoRazao.empresa_id == ids[0]))
            session.execute(delete(Usuario).where(Usuario.id == ids[1]))
            session.execute(delete(Empresa).where(Empresa.id == ids[0]))
        engine.dispose()


def _storage(tmp_path, sessions, clock=None):
    return RazaoStorage(tmp_path / "uploads", max_bytes=8192, min_free_bytes=0,
                        min_free_ratio=0, retention_seconds=60, sessions=sessions, clock=clock)


def _bind(session, ids, upload, *, status="queued", failed_at=None):
    lote = LoteImportacaoRazao(empresa_id=ids[0], usuario_id=ids[1],
                              original_filename="synthetic.xlsx", file_hash=upload.file_hash,
                              status=status, failed_at=failed_at)
    session.add(lote)
    upload.bind(session, lote)
    return lote.id


def test_cleanup_skips_locked_row_and_observes_only_committed_success(tmp_path, storage_db):
    """FOR UPDATE SKIP LOCKED evita apagar enquanto outro processo transaciona."""
    sessions, ids = storage_db
    storage = _storage(tmp_path, sessions)
    with storage.admit([b"postgres"]) as upload:
        with sessions.begin() as session:
            lote_id = _bind(session, ids, upload)
    other = _storage(tmp_path, sessions)
    with sessions() as session:
        lote = session.scalar(select(LoteImportacaoRazao).where(
            LoteImportacaoRazao.id == lote_id).with_for_update())
        lote.status = "completed"
        session.flush()
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(other.cleanup).result(timeout=5) == 0
        session.rollback()
    with storage.open_for_job(lote_id) as stream:
        assert stream.read() == b"postgres"
    with sessions.begin() as session:
        session.get(LoteImportacaoRazao, lote_id).status = "completed"
    assert other.cleanup() == 1


def test_retry_and_cleanup_cannot_remove_same_file_during_expiration(tmp_path, storage_db):
    """Retry possui arquivo e lote até commit, inclusive quando o relógio expira."""
    sessions, ids = storage_db
    now = [datetime.now(timezone.utc)]
    storage = _storage(tmp_path, sessions, lambda: now[0])
    with storage.admit([b"retry"]) as upload:
        with sessions.begin() as session:
            lote_id = _bind(session, ids, upload, status="failed", failed_at=now[0])
    other = _storage(tmp_path, sessions, lambda: now[0])
    with storage.retry_guard(lote_id) as (session, lote, stream):
        now[0] += timedelta(seconds=60)
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(other.cleanup).result(timeout=5) == 0
        lote.status = "queued"
        assert stream.read() == b"retry"
    assert other.cleanup() == 0
    with sessions.begin() as session:
        session.get(LoteImportacaoRazao, lote_id).status = "failed"
    assert other.cleanup() == 1
    with pytest.raises(TemporaryFileUnavailable):
        with storage.retry_guard(lote_id):
            pytest.fail("arquivo removido não permite retry")


def test_concurrent_retry_reports_busy_file(tmp_path, storage_db):
    sessions, ids = storage_db
    now = datetime.now(timezone.utc)
    storage = _storage(tmp_path, sessions, lambda: now)
    with storage.admit([b"retry-concorrente"]) as upload:
        with sessions.begin() as session:
            lote_id = _bind(session, ids, upload, status="failed", failed_at=now)

    other = _storage(tmp_path, sessions, lambda: now)
    with storage.retry_guard(lote_id):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_attempt_retry, other, lote_id)
            with pytest.raises(TemporaryFileBusy):
                future.result(timeout=5)


def _attempt_retry(storage, lote_id):
    with storage.retry_guard(lote_id):
        pytest.fail("retry concorrente não deve adquirir o arquivo")


def test_uncommitted_binding_is_protected_and_rollback_becomes_orphan(tmp_path, storage_db):
    """O vínculo ainda invisível no PostgreSQL não torna a admissão um órfão."""
    sessions, ids = storage_db
    storage = _storage(tmp_path, sessions)
    other = _storage(tmp_path, sessions)
    with storage.admit([b"rollback"]) as upload:
        with sessions() as session:
            _bind(session, ids, upload)
            with ThreadPoolExecutor(max_workers=1) as executor:
                assert executor.submit(other.cleanup).result(timeout=5) == 0
            session.rollback()
    assert other.cleanup() == 1
    with sessions() as session:
        assert session.scalar(select(LoteImportacaoRazao.id).where(
            LoteImportacaoRazao.empresa_id == ids[0])) is None


def test_valid_lease_blocks_cleanup_until_expiration(tmp_path, storage_db):
    """Lease válida impede exclusão mesmo em failed já fora da retenção."""
    sessions, ids = storage_db
    now = [datetime.now(timezone.utc)]
    storage = _storage(tmp_path, sessions, lambda: now[0])
    with storage.admit([b"lease"]) as upload:
        with sessions.begin() as session:
            lote_id = _bind(session, ids, upload, status="failed",
                            failed_at=now[0] - timedelta(hours=2))
            session.get(LoteImportacaoRazao, lote_id).lease_expires_at = now[0] + timedelta(seconds=30)
    assert storage.cleanup() == 0
    now[0] += timedelta(seconds=30)
    assert storage.cleanup() == 1
