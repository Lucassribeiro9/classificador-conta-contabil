"""Armazenamento privado de uploads do Razão, independente de HTTP e worker."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from math import ceil
from typing import BinaryIO, Iterable, Iterator
from sqlalchemy.orm import Session
from uuid import uuid4
import os
import fcntl
import shutil
import json
import re
from sqlalchemy import select
from core.models import LoteImportacaoRazao


class UploadTooLarge(Exception):
    """Erro seguro para tradução HTTP em 413 pela futura integração."""

    code = "upload_too_large"

    def __init__(self):
        super().__init__("Upload excede o limite permitido.")


class InsufficientCapacity(Exception):
    """Erro seguro para tradução HTTP em 507 pela futura integração."""

    code = "temporary_capacity_unavailable"

    def __init__(self):
        super().__init__("Capacidade temporária indisponível.")


class TemporaryFileUnavailable(FileNotFoundError):
    """Arquivo ausente, expirado ou ocupado; não contém caminhos internos."""

    code = "temporary_file_unavailable"

    def __init__(self):
        super().__init__("Arquivo temporário indisponível.")


class StoredUpload:
    """Handle interno válido somente durante o contexto de admissão."""

    def __init__(self, storage, key: str, stream: BinaryIO, size: int, file_hash: str):
        self.key = key
        self.size = size
        self.file_hash = file_hash
        self._stream = stream
        self._stream.seek(0)
        self._storage = storage
        self._bound = False

    def bind(self, session: Session, lote: LoteImportacaoRazao) -> None:
        """Vincula antes do commit, que deve ocorrer dentro da admissão."""
        if self._stream.closed or self._bound:
            raise ValueError("Handle de upload fechado ou já vinculado.")
        if lote.file_hash != self.file_hash:
            raise ValueError("Hash do lote diverge do upload.")
        if self._storage._sessions is None:
            raise ValueError("Vinculação exige fábrica de sessões para limpeza segura.")
        session.flush()
        self._storage._write_binding(self.key, lote.id)
        self._bound = True

    def read(self, size: int = 65536) -> bytes:
        """Lê sequencialmente com bloco limitado, sem expor caminho físico."""
        if size < 0:
            raise ValueError("Informe tamanho de bloco não negativo.")
        return self._stream.read(size)


class RazaoStorage:
    """Recebe chunks sem materializar o upload em memória."""

    def __init__(self, root, *, max_bytes, min_free_bytes, min_free_ratio, sessions=None,
                 retention_seconds=86400, clock=None):
        if (max_bytes <= 0 or min_free_bytes < 0 or not 0 <= min_free_ratio < 1
                or retention_seconds <= 0):
            raise ValueError("Limites de armazenamento inválidos.")
        self.retention_seconds = retention_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._sessions = sessions
        self._root = Path(root)
        if self._root.is_symlink():
            raise ValueError("O diretório privado não pode ser link simbólico.")
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._root.chmod(0o700)
        self.max_bytes = max_bytes
        self.min_free_bytes = min_free_bytes
        self.min_free_ratio = min_free_ratio

    @classmethod
    def from_settings(cls, settings, *, sessions=None):
        """Constrói o serviço com os limites validados da aplicação."""
        return cls(settings.RAZAO_STORAGE_DIR,
                   max_bytes=settings.RAZAO_UPLOAD_MAX_BYTES,
                   min_free_bytes=settings.RAZAO_STORAGE_MIN_FREE_BYTES,
                   min_free_ratio=settings.RAZAO_STORAGE_MIN_FREE_RATIO,
                   retention_seconds=settings.RAZAO_FAILED_RETENTION_SECONDS,
                   sessions=sessions)

    @contextmanager
    def _volume_lock(self):
        fd = os.open(self._root / ".storage.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _reserve(self, stream):
        usage = shutil.disk_usage(self._root)
        floor = max(self.min_free_bytes, ceil(usage.total * self.min_free_ratio))
        if usage.free - self.max_bytes < floor:
            raise InsufficientCapacity()
        try:
            os.posix_fallocate(stream.fileno(), 0, self.max_bytes)
            if shutil.disk_usage(self._root).free < floor:
                raise InsufficientCapacity()
        except OSError:
            raise InsufficientCapacity() from None

    @staticmethod
    def _sync_directory(directory):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _open_file(path):
        # Um descriptor não expõe caminho em stream.name e rejeita symlinks.
        return os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")

    def _write_binding(self, key, lote_id):
        directory = self._root / key
        with self._volume_lock():
            if any(self._binding(p) == lote_id for p in self._directories()):
                raise ValueError("Lote já possui vínculo com arquivo temporário.")
            try:
                fd = os.open(directory / "binding.tmp",
                             os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "w") as metadata:
                    json.dump({"lote_id": lote_id}, metadata)
                    metadata.flush()
                    os.fsync(metadata.fileno())
                os.replace(directory / "binding.tmp", directory / "binding.json")
                self._sync_directory(directory)
                self._sync_directory(self._root)
                usage = shutil.disk_usage(self._root)
                floor = max(self.min_free_bytes, ceil(usage.total * self.min_free_ratio))
                if usage.free < floor:
                    raise InsufficientCapacity()
            except OSError:
                raise InsufficientCapacity() from None

    def _binding(self, directory):
        path = directory / "binding.json"
        try:
            with self._open_file(path) as metadata:
                lote_id = json.load(metadata)["lote_id"]
            if type(lote_id) is not int or lote_id <= 0:
                raise ValueError("Vínculo temporário inválido; limpeza interrompida.")
            return lote_id
        except FileNotFoundError:
            return None

    def _directories(self):
        return [p for p in self._root.iterdir()
                if re.fullmatch(r"[0-9a-f]{32}", p.name) and p.is_dir() and not p.is_symlink()]

    def _remove(self, directory):
        for name in (f"{directory.name}.xlsx", "binding.json", "binding.tmp"):
            (directory / name).unlink(missing_ok=True)
        try:
            directory.rmdir()
        except FileNotFoundError:
            pass

    @staticmethod
    def _utc(value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    def _can_remove(self, lote):
        now = self._clock()
        if lote.status in ("queued", "processing"):
            return False
        if lote.lease_expires_at and self._utc(lote.lease_expires_at) > now:
            return False
        if lote.status in ("completed", "completed_with_warnings"):
            return True
        return (lote.status == "failed" and lote.failed_at is not None
                and self._utc(lote.failed_at) + timedelta(seconds=self.retention_seconds) <= now)

    def cleanup(self):
        """Remove sucesso confirmado sem disputar arquivo ou linha ocupados."""
        removed = 0
        with self._volume_lock():
            for directory in self._directories():
                try:
                    stream = self._open_file(directory / f"{directory.name}.xlsx")
                except FileNotFoundError:
                    # Criação do diretório e aquisição do arquivo usam a mesma trava.
                    # Sem arquivo não pode existir escritor ativo neste diretório.
                    self._remove(directory)
                    removed += 1
                    continue
                with stream:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    lote_id = self._binding(directory)
                    if lote_id is None:
                        self._remove(directory)
                        removed += 1
                        continue
                    if self._sessions is None:
                        continue
                    with self._sessions.begin() as session:
                        exists = session.scalar(select(LoteImportacaoRazao.id).where(
                            LoteImportacaoRazao.id == lote_id))
                        lote = session.scalar(select(LoteImportacaoRazao).where(
                            LoteImportacaoRazao.id == lote_id).with_for_update(skip_locked=True))
                        if exists is None or (lote is not None and self._can_remove(lote)):
                            self._remove(directory)
                            removed += 1
        return removed

    @contextmanager
    def open_for_job(self, lote_id):
        """Abre para consumo interno sob proteção contra exclusão."""
        stream = None
        with self._volume_lock():
            for directory in self._directories():
                if self._binding(directory) == lote_id:
                    try:
                        stream = self._open_file(directory / f"{directory.name}.xlsx")
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        if stream is not None:
                            stream.close()
                        raise TemporaryFileUnavailable() from None
                    break
        if stream is None:
            raise TemporaryFileUnavailable()
        try:
            yield stream
        finally:
            stream.close()

    @contextmanager
    def retry_guard(self, lote_id):
        """Protege arquivo e transação do retry até o commit feito ao sair."""
        with self.open_for_job(lote_id) as stream:
            with self._sessions.begin() as session:
                lote = session.scalar(select(LoteImportacaoRazao).where(
                    LoteImportacaoRazao.id == lote_id).with_for_update(skip_locked=True))
                if (lote is None or lote.status != "failed" or lote.failed_at is None
                        or self._can_remove(lote)
                        or (lote.lease_expires_at
                            and self._utc(lote.lease_expires_at) > self._clock())):
                    raise TemporaryFileUnavailable()
                yield session, lote, stream

    @contextmanager
    def admit(self, chunks: Iterable[bytes]) -> Iterator[StoredUpload]:
        """Mantém o arquivo privado até o consumidor concluir a admissão."""
        key = uuid4().hex
        directory = self._root / key
        path = directory / f"{key}.xlsx"
        upload = None
        try:
            try:
                with self._volume_lock():
                    directory.mkdir(mode=0o700)
                    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                    fcntl.flock(fd, fcntl.LOCK_EX)
            except OSError:
                raise InsufficientCapacity() from None
            with os.fdopen(fd, 'w+b') as stream:
                with self._volume_lock():
                    self._reserve(stream)
                try:
                    digest = sha256()
                    size = 0
                    for chunk in chunks:
                        if size + len(chunk) > self.max_bytes:
                            raise UploadTooLarge()
                        stream.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                    stream.truncate(size)
                    stream.flush()
                    os.fsync(stream.fileno())
                except OSError:
                    raise InsufficientCapacity() from None
                upload = StoredUpload(self, key, stream, size, digest.hexdigest())
                yield upload
        finally:
            if upload is None or not upload._bound:
                with self._volume_lock():
                    self._remove(directory)
