"""Aggregate metrics with a fixed, content-free label vocabulary."""

from prometheus_client import CollectorRegistry, Counter, Histogram, ProcessCollector

from core.database import SessionLocal


REGISTRY = CollectorRegistry(auto_describe=False)
ProcessCollector(registry=REGISTRY)
HTTP_REQUESTS = Counter(
    "classificador_http_requests_total",
    "HTTP requests grouped by template, method, and status class.",
    ("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "classificador_http_request_duration_seconds",
    "HTTP request duration grouped by template, method, and status class.",
    ("method", "route", "status"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=REGISTRY,
)
_ALLOWED_METHODS = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
)


def observe_http_request(
    method: str, route: str | None, status_code: int, duration_seconds: float
) -> None:
    """Record only route templates and bounded values, never the request URL."""
    labels = (
        method if method in _ALLOWED_METHODS else "OTHER",
        route if route and route.startswith("/") else "unmatched",
        f"{status_code // 100}xx" if 100 <= status_code <= 599 else "unknown",
    )
    HTTP_REQUESTS.labels(*labels).inc()
    HTTP_DURATION.labels(*labels).observe(duration_seconds)


def _private_bind_address(peer_host: str) -> str:
    """Find the local interface used to reach the private database network."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((peer_host, 5432))
        return probe.getsockname()[0]


def start_private_metrics_server(peer_host: str, port: int):
    """Serve API and durable metrics only on the database network interface."""
    from prometheus_client import start_http_server

    return start_http_server(
        port=port, addr=_private_bind_address(peer_host), registry=REGISTRY
    )


def start_private_process_metrics_server(peer_host: str, port: int):
    """Serve worker process health without loading API or database metrics."""
    from prometheus_client import start_http_server

    registry = CollectorRegistry(auto_describe=False)
    ProcessCollector(registry=registry)
    return start_http_server(
        port=port, addr=_private_bind_address(peer_host), registry=registry
    )


class OperationalCollector:
    """Read durable counts without exporting rows or tenant identifiers."""

    def __init__(self, sessions):
        self.sessions = sessions

    def collect(self):
        from datetime import datetime, timezone

        from prometheus_client.core import GaugeMetricFamily
        from sqlalchemy import func, select
        from sqlalchemy.exc import SQLAlchemyError

        from core.models import (
            LoteImportacaoRazao,
            MLJob,
            ModelVersion,
            MovimentoOperacionalImportado,
            ReviewItem,
        )

        jobs = GaugeMetricFamily(
            "classificador_ml_jobs",
            "ML jobs by kind and technical state.",
            labels=["kind", "status"],
        )
        queue_age = GaugeMetricFamily(
            "classificador_ml_job_queue_oldest_seconds",
            "Age of oldest queued ML job.",
            labels=["kind"],
        )
        progress = GaugeMetricFamily(
            "classificador_ml_job_progress_percent",
            "Mean progress of running ML jobs.",
            labels=["kind"],
        )
        reviews = GaugeMetricFamily(
            "classificador_review_items",
            "Review items by state.",
            labels=["status"],
        )
        batches = GaugeMetricFamily(
            "classificador_razao_batches",
            "Razao import batches by technical state.",
            labels=["status"],
        )
        invalid_lines = GaugeMetricFamily(
            "classificador_razao_invalid_lines", "Invalid Razao lines across batches."
        )
        warnings = GaugeMetricFamily(
            "classificador_razao_warnings", "Razao warnings across batches."
        )
        movements = GaugeMetricFamily(
            "classificador_ml_movements",
            "Operational movements by review state.",
            labels=["status"],
        )
        models = GaugeMetricFamily(
            "classificador_ml_models",
            "Model versions by lifecycle state.",
            labels=["status"],
        )
        try:
            with self.sessions() as session:
                for kind, status, count in session.execute(
                    select(MLJob.kind, MLJob.status, func.count()).group_by(
                        MLJob.kind, MLJob.status
                    )
                ):
                    if kind in {
                        "train",
                        "classify",
                        "classify_movements",
                    } and status in {
                        "queued",
                        "running",
                        "completed",
                        "failed",
                        "cancelled",
                    }:
                        jobs.add_metric([kind, status], count)
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                for kind, oldest in session.execute(
                    select(MLJob.kind, func.min(MLJob.created_at))
                    .where(MLJob.status == "queued")
                    .group_by(MLJob.kind)
                ):
                    if kind in {"train", "classify", "classify_movements"} and oldest:
                        queue_age.add_metric(
                            [kind], max(0, (now - oldest).total_seconds())
                        )
                for kind, mean_progress in session.execute(
                    select(MLJob.kind, func.avg(MLJob.progress))
                    .where(MLJob.status == "running")
                    .group_by(MLJob.kind)
                ):
                    if kind in {"train", "classify", "classify_movements"}:
                        progress.add_metric([kind], mean_progress)
                for status, count in session.execute(
                    select(ReviewItem.status, func.count()).group_by(ReviewItem.status)
                ):
                    if status in {"pending", "in_review", "resolved", "dismissed"}:
                        reviews.add_metric([status], count)
                for status, count in session.execute(
                    select(LoteImportacaoRazao.status, func.count()).group_by(
                        LoteImportacaoRazao.status
                    )
                ):
                    if status in {
                        "queued",
                        "processing",
                        "completed",
                        "completed_with_warnings",
                        "failed",
                    }:
                        batches.add_metric([status], count)
                invalid, warning_count = session.execute(
                    select(
                        func.coalesce(func.sum(LoteImportacaoRazao.total_invalidas), 0),
                        func.coalesce(func.sum(LoteImportacaoRazao.warnings_total), 0),
                    )
                ).one()
                for status, count in session.execute(
                    select(MovimentoOperacionalImportado.status, func.count()).group_by(
                        MovimentoOperacionalImportado.status
                    )
                ):
                    if status in {
                        "pendente",
                        "pre_classificado",
                        "sugerido",
                        "revisao",
                        "aprovado",
                        "corrigido",
                        "rejeitado",
                        "convertido",
                    }:
                        movements.add_metric([status], count)
                for status, count in session.execute(
                    select(ModelVersion.status, func.count()).group_by(
                        ModelVersion.status
                    )
                ):
                    if status in {"candidate", "active", "retired"}:
                        models.add_metric([status], count)
        except SQLAlchemyError:
            db_status = 0
        else:
            invalid_lines = GaugeMetricFamily(
                "classificador_razao_invalid_lines",
                "Invalid Razao lines across batches.",
                value=invalid,
            )
            warnings = GaugeMetricFamily(
                "classificador_razao_warnings",
                "Razao warnings across batches.",
                value=warning_count,
            )
            db_status = 1
        yield jobs
        yield queue_age
        yield progress
        yield reviews
        yield batches
        yield invalid_lines
        yield warnings
        yield models
        yield movements
        yield GaugeMetricFamily(
            "classificador_operational_db_up",
            "Operational database scrape succeeded.",
            value=db_status,
        )


REGISTRY.register(OperationalCollector(SessionLocal))
