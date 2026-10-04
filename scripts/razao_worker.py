"""Processo executável dos consumidores da fila assíncrona do Razão."""

from __future__ import annotations

from os import getenv
from signal import SIGINT, SIGTERM, signal
from socket import gethostname
from threading import Event, Thread

from core.config import settings
from core.database import SessionLocal
from core.razao_storage import RazaoStorage
from core.razao_worker import build_workers, process_razao_upload
from core.technical_logging import configure_technical_logging


def run_worker_loop(worker, storage, *, poll_seconds: float, stop_event: Event) -> None:
    """Consome jobs até o encerramento e limpa órfãos apenas quando ocioso."""
    while not stop_event.is_set():
        if worker.run_once():
            continue
        storage.cleanup()
        stop_event.wait(poll_seconds)


def main() -> None:
    configure_technical_logging(
        service="razao-worker",
        log_dir=settings.TECHNICAL_LOG_DIR,
    )
    stop_event = Event()
    signal(SIGTERM, lambda *_: stop_event.set())
    signal(SIGINT, lambda *_: stop_event.set())
    storage = RazaoStorage.from_settings(settings, sessions=SessionLocal)
    worker_id = getenv("HOSTNAME") or gethostname() or "razao-worker"
    workers = build_workers(
        SessionLocal,
        storage,
        process_razao_upload,
        worker_id=worker_id,
        settings=settings,
    )
    threads = [
        Thread(
            target=run_worker_loop,
            kwargs={
                "worker": worker,
                "storage": storage,
                "poll_seconds": settings.RAZAO_POLL_INTERVAL_SECONDS,
                "stop_event": stop_event,
            },
            name=f"razao-consumer-{index}",
        )
        for index, worker in enumerate(workers, start=1)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()
