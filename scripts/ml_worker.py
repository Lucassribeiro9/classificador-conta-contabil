"""Independent consumers for the ml/cpu pool."""

from os import getenv
from signal import SIGINT, SIGTERM, signal
from socket import gethostname
from threading import Event, Thread

from core.config import settings
from core.database import SessionLocal
from core.ml_worker import MLWorker
from core.operational_metrics import start_private_process_metrics_server
from core.technical_logging import configure_technical_logging


def run_worker_loop(worker: MLWorker, *, stop_event: Event) -> None:
    while not stop_event.is_set():
        if worker.run_once():
            continue
        stop_event.wait(settings.ML_JOB_POLL_INTERVAL_SECONDS)


def main() -> None:
    configure_technical_logging(service="ml-worker", log_dir=settings.TECHNICAL_LOG_DIR)
    metrics_server = None
    metrics_thread = None
    if settings.METRICS_NETWORK_PEER:
        metrics_server, metrics_thread = start_private_process_metrics_server(
            settings.METRICS_NETWORK_PEER, settings.METRICS_PORT
        )
    try:
        stop = Event()
        signal(SIGTERM, lambda *_: stop.set())
        signal(SIGINT, lambda *_: stop.set())
        host = getenv("HOSTNAME") or gethostname() or "ml-worker"
        threads = []
        for index in range(settings.ML_CPU_WORKER_CONCURRENCY):
            worker = MLWorker(
                SessionLocal, worker_id=f"{host}-{index + 1}",
                model_dir=settings.MODEL_DIR,
                lease_seconds=settings.ML_JOB_LEASE_SECONDS,
            )
            thread = Thread(target=run_worker_loop, kwargs={"worker": worker, "stop_event": stop},
                            name=f"ml-consumer-{index + 1}")
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        if metrics_server is not None:
            metrics_server.shutdown()
            metrics_server.server_close()
            metrics_thread.join(timeout=2)


if __name__ == "__main__":
    main()
