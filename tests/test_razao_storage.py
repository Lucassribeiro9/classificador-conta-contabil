"""Contrato do armazenamento temporário, usando arquivos reais e dados sintéticos."""

from hashlib import sha256

from core.razao_storage import RazaoStorage


def test_streams_chunks_to_private_random_file_without_retaining_unbound_upload(tmp_path):
    """O consumidor recebe bytes íntegros; upload sem lote não deixa arquivo."""
    storage = RazaoStorage(tmp_path, max_bytes=16, min_free_bytes=0, min_free_ratio=0)
    with storage.admit(iter([b"plan", b"ilha"])) as upload:
        assert upload.size == 8
        assert upload.file_hash == sha256(b"planilha").hexdigest()
        assert upload.read() == b"planilha"
        assert len(upload.key) == 32
        assert next(tmp_path.glob("*/*.xlsx")).stem == upload.key
        assert str(tmp_path) not in repr(upload)
    assert not list(tmp_path.glob("*/*.xlsx"))


def test_rejects_over_limit_before_writing_extra_chunk_and_releases_partial_file(tmp_path):
    """O limite exato é aceito e um byte adicional interrompe o recebimento."""
    import pytest
    from core.razao_storage import UploadTooLarge

    storage = RazaoStorage(tmp_path, max_bytes=8, min_free_bytes=0, min_free_ratio=0)
    with storage.admit([b"1234", b"5678"]) as upload:
        assert upload.size == 8
    with pytest.raises(UploadTooLarge, match="limite") as error:
        with storage.admit([b"12345678", b"9"]):
            pytest.fail("upload excedido foi admitido")
    assert error.value.code == "upload_too_large"
    assert not list(tmp_path.glob("*/*.xlsx"))


def test_reserves_maximum_before_consuming_and_rejects_insufficient_capacity(tmp_path):
    """A reserva ocorre antes de consumir chunks e respeita o piso do volume."""
    import pytest
    from core.razao_storage import InsufficientCapacity

    consumed = []

    def chunks():
        consumed.append(True)
        yield b"x"

    storage = RazaoStorage(
        tmp_path, max_bytes=16, min_free_bytes=10**20, min_free_ratio=0
    )
    with pytest.raises(InsufficientCapacity) as error:
        with storage.admit(chunks()):
            pytest.fail("admitiu sem espaço")
    assert error.value.code == "temporary_capacity_unavailable"
    assert not consumed
    assert not list(tmp_path.glob("*/*.xlsx"))


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base
from core.models import Empresa, Usuario, LoteImportacaoRazao


@pytest.fixture
def sessions(tmp_path):
    """Banco isolado para contratos sem concorrência de row locks."""
    engine = create_engine(f"sqlite:///{tmp_path / 'storage-test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as session:
        session.add(Empresa(nome_empresa="Sintética", cnpj_cpf="55666777000188",
                            api_key="synthetic", cod_dominio=7701))
        session.add(Usuario(nome="Teste", login="storage", email="storage@example.com",
                            senha_hash="synthetic", papel="operador"))
    yield factory
    engine.dispose()


def test_bound_upload_survives_context_and_remains_available_for_queued_job(tmp_path, sessions):
    """Associação privada sobrevive ao reinício do serviço após commit do lote."""
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions)
    with storage.admit([b"planilha"]) as upload:
        with sessions.begin() as session:
            lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                      original_filename="original.xlsx", file_hash=upload.file_hash)
            session.add(lote)
            upload.bind(session, lote)
            lote_id = lote.id
    restarted = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                             min_free_bytes=0, min_free_ratio=0, sessions=sessions)
    assert restarted.cleanup() == 0
    with restarted.open_for_job(lote_id) as stream:
        assert stream.read() == b"planilha"


def test_cleanup_deletes_committed_success_but_preserves_rollback(tmp_path, sessions):
    """Limpeza observa somente o resultado confirmado no banco."""
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions)
    with storage.admit([b"planilha"]) as upload:
        with sessions.begin() as session:
            lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                      original_filename="original.xlsx", file_hash=upload.file_hash)
            session.add(lote)
            upload.bind(session, lote)
            lote_id = lote.id
    with sessions() as session:
        session.get(LoteImportacaoRazao, lote_id).status = "completed"
        session.flush()
        assert storage.cleanup() == 0
        session.rollback()
    with storage.open_for_job(lote_id) as stream:
        assert stream.read() == b"planilha"
    with sessions.begin() as session:
        session.get(LoteImportacaoRazao, lote_id).status = "completed"
    assert storage.cleanup() == 1
    with pytest.raises(FileNotFoundError):
        with storage.open_for_job(lote_id):
            pytest.fail("arquivo concluído ainda existe")


from datetime import datetime, timedelta, timezone


@pytest.mark.parametrize("status,lease_seconds,age_seconds,removed", [
    ("failed", None, 3599, 0), ("failed", None, 3600, 1),
    ("failed", 60, 7200, 0), ("completed", 60, 7200, 0),
    ("queued", None, 7200, 0), ("processing", -1, 7200, 0),
    ("completed_with_warnings", None, 0, 1),
])
def test_cleanup_respects_retention_and_never_deletes_active_jobs(
    tmp_path, sessions, status, lease_seconds, age_seconds, removed
):
    """Retenção é relativa à falha, e lease válida prevalece sobre exclusão."""
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions,
                           retention_seconds=3600, clock=lambda: now)
    with storage.admit([b"planilha"]) as upload:
        with sessions.begin() as session:
            lote = LoteImportacaoRazao(
                empresa_id=1, usuario_id=1, original_filename="original.xlsx",
                file_hash=upload.file_hash, status=status,
                failed_at=now - timedelta(seconds=age_seconds),
                lease_expires_at=None if lease_seconds is None else now + timedelta(seconds=lease_seconds)
            )
            session.add(lote)
            upload.bind(session, lote)
    assert storage.cleanup() == removed


def test_retry_guard_preserves_file_while_retry_commits_and_rejects_expired_file(tmp_path, sessions):
    """Retry e limpeza compartilham a posse do arquivo e o bloqueio do lote."""
    from core.razao_storage import TemporaryFileUnavailable

    now = [datetime(2026, 9, 9, tzinfo=timezone.utc)]
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions,
                           retention_seconds=60, clock=lambda: now[0])
    with storage.admit([b"retry"]) as upload:
        with sessions.begin() as session:
            lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                      original_filename="retry.xlsx", file_hash=upload.file_hash,
                                      status="failed", failed_at=now[0])
            session.add(lote)
            upload.bind(session, lote)
            lote_id = lote.id
    with storage.retry_guard(lote_id) as (session, lote, stream):
        now[0] += timedelta(seconds=60)
        assert storage.cleanup() == 0
        assert stream.read() == b"retry"
        lote.status = "queued"
    assert storage.cleanup() == 0
    with sessions.begin() as session:
        session.get(LoteImportacaoRazao, lote_id).status = "failed"
    with pytest.raises(TemporaryFileUnavailable):
        with storage.retry_guard(lote_id):
            pytest.fail("retry após retenção foi aceito")
    assert storage.cleanup() == 1


def test_settings_supply_validated_environment_overrides(tmp_path, monkeypatch):
    """Limites operacionais podem mudar por ambiente sem alterar código."""
    from core.config import Settings
    from pydantic import ValidationError

    config = Settings(_env_file=None)
    assert config.RAZAO_UPLOAD_MAX_BYTES == 50_000_000
    assert config.RAZAO_STORAGE_MIN_FREE_BYTES == 5_000_000_000
    assert config.RAZAO_STORAGE_MIN_FREE_RATIO == 0.15
    assert config.RAZAO_FAILED_RETENTION_SECONDS == 86400
    monkeypatch.setenv("RAZAO_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("RAZAO_UPLOAD_MAX_BYTES", "8")
    monkeypatch.setenv("RAZAO_STORAGE_MIN_FREE_BYTES", "0")
    monkeypatch.setenv("RAZAO_STORAGE_MIN_FREE_RATIO", "0")
    storage = RazaoStorage.from_settings(Settings(_env_file=None))
    with storage.admit([b"12345678"]) as upload:
        assert upload.size == 8
    monkeypatch.setenv("RAZAO_UPLOAD_MAX_BYTES", "0")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_filesystem_failure_is_safe_and_releases_reservation(tmp_path, monkeypatch):
    """Falha ao confirmar bytes no disco não vaza caminho nem deixa reserva."""
    import os
    from core.razao_storage import InsufficientCapacity

    storage = RazaoStorage(tmp_path, max_bytes=16, min_free_bytes=0, min_free_ratio=0)

    def fail_sync(fd):
        raise OSError(28, "No space left", str(tmp_path / "private.xlsx"))

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(InsufficientCapacity) as error:
        with storage.admit([b"bytes"]):
            pytest.fail("arquivo não durável foi aceito")
    assert str(tmp_path) not in str(error.value)
    assert not list(tmp_path.glob("*/*.xlsx"))


import multiprocessing
import os
from collections import namedtuple
from pathlib import Path


def _paused_upload(root, ready, release):
    """Processo interrompível após reservar espaço e antes de concluir upload."""
    storage = RazaoStorage(root, max_bytes=4096, min_free_bytes=0, min_free_ratio=0)

    def chunks():
        yield b"partial"
        ready.set()
        release.wait(10)
        yield b"final"

    with storage.admit(chunks()):
        pass


def test_cleanup_preserves_active_admission_and_recovers_after_process_death(tmp_path):
    """A morte do processo libera flock, permitindo recolher a reserva órfã."""
    ctx = multiprocessing.get_context("spawn")
    ready, release = ctx.Event(), ctx.Event()
    child = ctx.Process(target=_paused_upload, args=(tmp_path, ready, release))
    child.start()
    try:
        assert ready.wait(10)
        storage = RazaoStorage(tmp_path, max_bytes=4096, min_free_bytes=0, min_free_ratio=0)
        assert storage.cleanup() == 0
        child.kill()
        child.join(5)
        assert storage.cleanup() == 1
        assert not list(tmp_path.glob("*/*.xlsx"))
    finally:
        if child.is_alive():
            child.kill()
        child.join(5)


def _competing_admission(root, barrier, results, release):
    """Disco controlado; alocação e coordenação entre processos são reais."""
    import shutil
    usage = namedtuple("usage", "total used free")

    def disk_usage(path):
        allocated = sum(p.stat().st_blocks * 512 for p in Path(root).glob("*/*.xlsx"))
        return usage(16384, allocated, 8192 - allocated)

    shutil.disk_usage = disk_usage
    storage = RazaoStorage(root, max_bytes=4096, min_free_bytes=4096, min_free_ratio=0)

    def chunks():
        results.put("admitted")
        release.wait(10)
        yield b"data"

    from core.razao_storage import InsufficientCapacity
    barrier.wait(5)
    try:
        with storage.admit(chunks()):
            pass
    except InsufficientCapacity:
        results.put("rejected")


def test_concurrent_admissions_reserve_space_once_across_processes(tmp_path):
    """Somente um upload cabe no piso; a reserva física impede sobre-admissão."""
    ctx = multiprocessing.get_context("spawn")
    barrier, results, release = ctx.Barrier(2), ctx.Queue(), ctx.Event()
    children = [ctx.Process(target=_competing_admission,
                            args=(tmp_path, barrier, results, release)) for _ in range(2)]
    for child in children:
        child.start()
    try:
        assert sorted([results.get(timeout=10), results.get(timeout=10)]) == ["admitted", "rejected"]
    finally:
        release.set()
        for child in children:
            child.join(5)
            if child.is_alive():
                child.kill()
                child.join(5)
        results.close()
    assert all(child.exitcode == 0 for child in children)
    assert not list(tmp_path.glob("*/*.xlsx"))


def test_capacity_accounts_for_allocation_granularity(tmp_path, monkeypatch):
    """Um upload de um byte ainda consome um bloco físico inteiro."""
    import shutil
    from core.razao_storage import InsufficientCapacity
    usage = namedtuple("usage", "total used free")

    def disk_usage(path):
        allocated = sum(p.stat().st_blocks * 512 for p in tmp_path.glob("*/*.xlsx"))
        return usage(10000, allocated, 4096 - allocated)

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    storage = RazaoStorage(tmp_path, max_bytes=1, min_free_bytes=4095, min_free_ratio=0)
    with pytest.raises(InsufficientCapacity):
        with storage.admit([b"x"]):
            pytest.fail("alocação física ultrapassou piso")
    assert not list(tmp_path.glob("*/*.xlsx"))


def test_second_upload_cannot_replace_canonical_file_binding(tmp_path, sessions):
    """Uploads idempotentes não podem deixar duas cópias associadas ao lote."""
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions)
    with storage.admit([b"canonical"]) as upload:
        with sessions.begin() as session:
            lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                      original_filename="original.xlsx", file_hash=upload.file_hash)
            session.add(lote)
            upload.bind(session, lote)
            lote_id = lote.id
    with pytest.raises(ValueError, match="vínculo"):
        with storage.admit([b"canonical"]) as duplicate:
            with sessions.begin() as session:
                duplicate.bind(session, session.get(LoteImportacaoRazao, lote_id))
    assert len(list((tmp_path / "uploads").glob("*/*.xlsx"))) == 1
    with storage.open_for_job(lote_id) as stream:
        assert stream.read() == b"canonical"


def test_interrupted_stream_frees_all_files_and_never_creates_lote(tmp_path, sessions):
    """Exceção do produtor aborta a admissão antes de qualquer lote existir."""
    from sqlalchemy import select, func
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions)

    def chunks():
        yield b"partial"
        raise RuntimeError("recebimento interrompido")

    with pytest.raises(RuntimeError, match="interrompido"):
        with storage.admit(chunks()):
            pytest.fail("upload incompleto foi admitido")
    assert not list((tmp_path / "uploads").glob("*/*.xlsx"))
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(LoteImportacaoRazao)) == 0


def test_failed_binding_flush_releases_file_without_committing_lote(tmp_path, sessions, monkeypatch):
    """Sem vínculo durável, a exceção faz rollback e remove também metadados parciais."""
    from core.razao_storage import InsufficientCapacity
    storage = RazaoStorage(tmp_path / "uploads", max_bytes=16,
                           min_free_bytes=0, min_free_ratio=0, sessions=sessions)
    with pytest.raises(InsufficientCapacity):
        with storage.admit([b"binding"]) as upload:
            def fail_sync(fd):
                raise OSError(28, "synthetic full disk")
            monkeypatch.setattr(os, "fsync", fail_sync)
            with sessions.begin() as session:
                lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                          original_filename="file.xlsx", file_hash=upload.file_hash)
                session.add(lote)
                upload.bind(session, lote)
    assert not list((tmp_path / "uploads").glob("*/*.xlsx"))
    assert not list((tmp_path / "uploads").glob("*/binding*"))


def test_private_permissions_and_safe_handle(tmp_path):
    """Arquivos ficam acessíveis só ao dono e o handle não contém caminho físico."""
    import stat
    storage = RazaoStorage(tmp_path, max_bytes=16, min_free_bytes=0, min_free_ratio=0)
    with storage.admit([b"private"]) as upload:
        path = next(tmp_path.glob("*/*.xlsx"))
        assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert upload.read(3) == b"pri"
        assert upload.read(4) == b"vate"


def test_binding_metadata_must_also_preserve_capacity_floor(tmp_path, sessions, monkeypatch):
    """Metadados não podem consumir o piso depois de reservar o XLSX."""
    import shutil
    from core.razao_storage import InsufficientCapacity
    root = tmp_path / "uploads"
    usage = namedtuple("usage", "total used free")

    def disk_usage(path):
        allocated = sum(p.stat().st_blocks * 512 for p in root.rglob("*") if p.is_file())
        return usage(16384, allocated, 8192 - allocated)

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    storage = RazaoStorage(root, max_bytes=4096, min_free_bytes=4096,
                           min_free_ratio=0, sessions=sessions)
    with pytest.raises(InsufficientCapacity):
        with storage.admit([b"x" * 4096]) as upload:
            with sessions.begin() as session:
                lote = LoteImportacaoRazao(empresa_id=1, usuario_id=1,
                                          original_filename="file.xlsx", file_hash=upload.file_hash)
                session.add(lote)
                upload.bind(session, lote)
    assert not list(root.glob("*/*.xlsx"))
