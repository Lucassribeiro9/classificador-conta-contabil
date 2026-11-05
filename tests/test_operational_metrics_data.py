"""Durable, aggregate operational metrics from synthetic records."""

from prometheus_client import CollectorRegistry, generate_latest

from core.models import Empresa, MLJob, ReviewItem
from tests.conftest import TestingSessionLocal


def test_scrape_aggregates_jobs_and_reviews_without_company_data(setup_db):
    from core.operational_metrics import OperationalCollector

    private_example = "empresa-super-secreta-508"
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa=private_example,
            api_key="metric-key-508",
            cnpj_cpf="12345678000199",
            cod_dominio=508,
        )
        session.add(company)
        session.flush()
        session.add(
            MLJob(
                empresa_id=company.id,
                kind="train",
                pool="ml/cpu",
                idempotency_key="metrics-1",
                payload_hash="a" * 64,
                payload={"historico": private_example},
                status="queued",
                progress=0,
            )
        )
        session.add(
            ReviewItem(
                empresa_id=company.id,
                source_type="movimento",
                grouping_key="secret-group",
                summary=private_example,
                criticality="high",
                status="pending",
            )
        )
        session.commit()

    registry = CollectorRegistry(auto_describe=True)
    registry.register(OperationalCollector(TestingSessionLocal))
    sample = generate_latest(registry).decode("utf-8")
    assert 'classificador_ml_jobs{kind="train",status="queued"} 1.0' in sample
    assert 'classificador_review_items{status="pending"} 1.0' in sample
    assert "classificador_operational_db_up 1.0" in sample
    assert private_example not in sample
    assert "metric-key-508" not in sample
    assert "secret-group" not in sample


def test_scrape_reports_import_quality_and_model_lifecycle(setup_db):
    from core.models import DatasetManifest, LoteImportacaoRazao, ModelVersion, Usuario
    from core.operational_metrics import OperationalCollector

    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Cliente sintético",
            api_key="metric-key-509",
            cnpj_cpf="12345678000200",
            cod_dominio=509,
        )
        user = Usuario(
            nome="Operador",
            login="metrics-user",
            email="metrics@example.com",
            senha_hash="synthetic-hash",
            papel="operador",
        )
        session.add_all([company, user])
        session.flush()
        session.add(
            LoteImportacaoRazao(
                empresa_id=company.id,
                usuario_id=user.id,
                original_filename="synthetic.xlsx",
                file_hash="metric-batch-508",
                status="completed_with_warnings",
                total_linhas=4,
                linhas_processadas=4,
                total_importadas=2,
                total_invalidas=2,
                warnings_total=1,
            )
        )
        manifest = DatasetManifest(
            empresa_id=company.id,
            content_hash="b" * 64,
            content={},
        )
        session.add(manifest)
        session.flush()
        session.add(
            ModelVersion(
                empresa_id=company.id,
                manifest_id=manifest.id,
                status="candidate",
                artifact_path="private/model.joblib",
                artifact_sha256="c" * 64,
                metrics={"macro_f1": 0.5},
            )
        )
        session.commit()

    registry = CollectorRegistry(auto_describe=True)
    registry.register(OperationalCollector(TestingSessionLocal))
    sample = generate_latest(registry).decode("utf-8")
    assert 'classificador_razao_batches{status="completed_with_warnings"} 1.0' in sample
    assert "classificador_razao_invalid_lines 2.0" in sample
    assert "classificador_razao_warnings 1.0" in sample
    assert 'classificador_ml_models{status="candidate"} 1.0' in sample
    assert "synthetic.xlsx" not in sample
    assert "private/model.joblib" not in sample


def test_scrape_reports_queue_age_and_running_progress(setup_db):
    from datetime import datetime, timedelta

    from core.operational_metrics import OperationalCollector

    now = datetime.now()
    with TestingSessionLocal() as session:
        queued_company = Empresa(
            nome_empresa="Fila",
            api_key="metric-key-510",
            cnpj_cpf="12345678000300",
            cod_dominio=510,
        )
        running_company = Empresa(
            nome_empresa="Execução",
            api_key="metric-key-511",
            cnpj_cpf="12345678000400",
            cod_dominio=511,
        )
        session.add_all([queued_company, running_company])
        session.flush()
        session.add_all(
            [
                MLJob(
                    empresa_id=queued_company.id,
                    kind="classify",
                    pool="ml/cpu",
                    idempotency_key="queued-metric",
                    payload_hash="d" * 64,
                    payload={},
                    status="queued",
                    progress=0,
                    created_at=now - timedelta(minutes=2),
                ),
                MLJob(
                    empresa_id=running_company.id,
                    kind="train",
                    pool="ml/cpu",
                    idempotency_key="running-metric",
                    payload_hash="e" * 64,
                    payload={},
                    status="running",
                    progress=40,
                    lease_token="lease-metric",
                    lease_owner="worker-metric",
                    lease_expires_at=now + timedelta(minutes=2),
                ),
            ]
        )
        session.commit()

    registry = CollectorRegistry(auto_describe=True)
    registry.register(OperationalCollector(TestingSessionLocal))
    sample = generate_latest(registry).decode("utf-8")
    age_line = next(
        line
        for line in sample.splitlines()
        if line.startswith('classificador_ml_job_queue_oldest_seconds{kind="classify"}')
    )
    assert 115 <= float(age_line.split()[-1]) <= 130
    assert 'classificador_ml_job_progress_percent{kind="train"} 40.0' in sample


def test_scrape_counts_ml_suggestions_and_abstentions_without_movement_content(
    setup_db,
):
    from datetime import date
    from decimal import Decimal

    from core.models import (
        LoteImportacaoMovimentoOperacional,
        MovimentoOperacionalImportado,
        Usuario,
    )
    from core.operational_metrics import OperationalCollector

    secret = "histórico privado 508"
    with TestingSessionLocal() as session:
        company = Empresa(
            nome_empresa="Empresa ML",
            api_key="metric-key-512",
            cnpj_cpf="12345678000500",
            cod_dominio=512,
        )
        user = Usuario(
            nome="Operador",
            login="metrics-ml-user",
            email="metrics-ml@example.com",
            senha_hash="synthetic-hash",
            papel="operador",
        )
        session.add_all([company, user])
        session.flush()
        batch = LoteImportacaoMovimentoOperacional(
            empresa_id=company.id,
            usuario_id=user.id,
            original_filename="private.xlsx",
            file_hash="metric-movement-batch",
            status="completed",
            periodo_inicio=date(2026, 1, 1),
            periodo_fim=date(2026, 1, 31),
            cnpj_cpf_arquivo="12345678000500",
        )
        session.add(batch)
        session.flush()
        for line, status in enumerate(("sugerido", "revisao"), start=1):
            session.add(
                MovimentoOperacionalImportado(
                    lote_id=batch.id,
                    empresa_id=company.id,
                    data=date(2026, 1, line),
                    conta_financeira=1234,
                    historico=secret,
                    historico_normalizado=secret,
                    valor_original=Decimal("10.00"),
                    valor_absoluto=Decimal("10.00"),
                    direcao="debito",
                    linha_original=line,
                    status=status,
                )
            )
        session.commit()

    registry = CollectorRegistry(auto_describe=True)
    registry.register(OperationalCollector(TestingSessionLocal))
    sample = generate_latest(registry).decode("utf-8")
    assert 'classificador_ml_movements{status="sugerido"} 1.0' in sample
    assert 'classificador_ml_movements{status="revisao"} 1.0' in sample
    assert secret not in sample
    assert "private.xlsx" not in sample


def test_failed_database_scrape_reports_only_health_flag():
    from sqlalchemy.exc import SQLAlchemyError

    from core.operational_metrics import OperationalCollector

    def unavailable_sessions():
        raise SQLAlchemyError("password=private-508")

    registry = CollectorRegistry(auto_describe=True)
    registry.register(OperationalCollector(unavailable_sessions))
    sample = generate_latest(registry).decode("utf-8")
    assert "classificador_operational_db_up 0.0" in sample
    assert "private-508" not in sample
