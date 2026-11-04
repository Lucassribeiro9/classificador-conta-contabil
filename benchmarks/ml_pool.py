"""Controlled synthetic training benchmark on a disposable local PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from core.ml_jobs import enqueue_ml_job
from core.ml_worker import MLWorker
from core.models import (
    ContaContabil, ContaContabilEmpresa, Empresa, LancamentoRazaoNormalizado,
    LoteImportacaoRazao, MLJob, Usuario,
)
from core.plano_contas_snapshots import importar_snapshot


def _test_database_url() -> str:
    url = environ["DATABASE_URL"]
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or parsed.host not in {"localhost", "127.0.0.1"}:
        raise SystemExit("Benchmark requer PostgreSQL descartavel em loopback")
    if parsed.database != "mljobs":
        raise SystemExit("Benchmark requer banco descartavel chamado mljobs")
    return url


def _seed_jobs(sessions, *, count: int, suffix: str) -> list[int]:
    codes = (10046, 50057, 70001)
    with sessions() as session:
        user = Usuario(
            nome=f"Benchmark {suffix}", login=f"benchmark-{suffix}",
            email=f"benchmark-{suffix}@example.invalid", senha_hash="benchmark-only",
            papel="operador", is_active=True,
        )
        session.add(user)
        for code in codes:
            if session.scalar(select(ContaContabil).where(ContaContabil.codigo == code)) is None:
                session.add(ContaContabil(
                    codigo=code, classificacao=f"1.1.{code}", nome=f"Conta {code}",
                    tipo="A", grau=4, is_active=True,
                    is_financial_origin=code == 10046,
                ))
        session.flush()
        companies = []
        for index in range(count):
            unique = uuid4().hex[:10]
            company = Empresa(
                nome_empresa=f"Benchmark {suffix} {index}",
                api_key=f"benchmark-{unique}",
                cnpj_cpf=f"{int(unique, 16) % 10**14:014d}",
                cod_dominio=int(unique, 16) % 2_000_000_000,
            )
            batch = LoteImportacaoRazao(
                empresa=company, usuario=user, original_filename="synthetic.xlsx",
                file_hash=f"sha256:{unique}", status="completed",
            )
            session.add_all([company, batch])
            for row_index in range(10):
                target = (50057, 70001)[row_index % 2]
                session.add(LancamentoRazaoNormalizado(
                    lote=batch, empresa=company, numero_lancamento=str(row_index),
                    data=date(2026, 1, 15), conta_origem=10046,
                    conta_contrapartida=target, conta_debito=target,
                    conta_credito=10046, direcao="credito",
                    historico=f"Pagamento sintetico {row_index}",
                    historico_normalizado=f"pagamento sintetico {row_index}",
                    valor=Decimal("100.00"),
                ))
            companies.append(company)
        session.commit()
        ids = []
        for company in companies:
            importar_snapshot(
                session, empresa_id=company.id,
                contas=[{
                    "codigo": code, "classificacao": f"1.1.{code}",
                    "nome": f"Conta {code}", "tipo": "A", "grau": 4,
                } for code in codes],
                vigencia=date(2026, 1, 1), origem="benchmark-sintetico",
            )
            account = session.query(ContaContabilEmpresa).filter_by(
                empresa_id=company.id, codigo=10046,
            ).one()
            account.is_financial_origin = True
            job = enqueue_ml_job(
                session, company_id=company.id, kind="train",
                idempotency_key=f"benchmark-{suffix}", payload={},
            )
            ids.append(job.id)
        session.commit()
        return ids


def main() -> None:
    engine = create_engine(_test_database_url())
    sessions = sessionmaker(bind=engine)
    try:
        with TemporaryDirectory(prefix="ml-pool-benchmark-") as model_dir:
            for concurrency in (1, 2):
                ids = _seed_jobs(sessions, count=4, suffix=uuid4().hex[:8])

                def run(index: int) -> bool:
                    worker = MLWorker(
                        sessions, worker_id=f"benchmark-{concurrency}-{index}",
                        model_dir=Path(model_dir),
                    )
                    return worker.run_once()

                started = perf_counter()
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    claimed = list(pool.map(run, range(4)))
                elapsed = perf_counter() - started
                with Session(engine) as session:
                    statuses = session.scalars(select(MLJob.status).where(MLJob.id.in_(ids))).all()
                if not all(claimed) or statuses != ["completed"] * 4:
                    raise SystemExit("Benchmark nao concluiu os quatro treinos")
                print(f"workers={concurrency} jobs=4 elapsed_seconds={elapsed:.3f}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
