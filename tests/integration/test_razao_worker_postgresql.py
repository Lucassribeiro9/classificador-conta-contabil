"""Concorrência e posse do worker contra PostgreSQL real."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from core.models import AuditEvent, Empresa, LoteImportacaoRazao, Usuario, WarningImportacaoRazao
from core.razao_worker import JobResult, LeaseLost, RazaoWorker


pytestmark = pytest.mark.integration_postgres


class FakeStorage:
    class Open:
        def __enter__(self):
            return object()

        def __exit__(self, *_):
            return False

    def open_for_job(self, _lote_id):
        return self.Open()

    def cleanup(self):
        pass


def _context():
    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url and make_url(database_url).get_backend_name() == "postgresql"
    engine = create_engine(database_url)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    suffix = uuid4().hex[:10]
    with sessions.begin() as session:
        empresa = Empresa(
            nome_empresa=f"Worker {suffix}",
            cnpj_cpf=str(int(suffix, 16) % 10**14).zfill(14),
            api_key=f"key-{suffix}",
            cod_dominio=int(suffix, 16) % 2_000_000_000,
        )
        usuario = Usuario(
            nome="Worker", login=f"worker-{suffix}", email=f"worker-{suffix}@example.com",
            senha_hash="hash", papel="operador",
        )
        session.add_all([empresa, usuario])
        session.flush()
        lotes = [
            LoteImportacaoRazao(
                empresa_id=empresa.id, usuario_id=usuario.id,
                original_filename=f"razao-{index}.xlsx", file_hash=f"sha256:{suffix}:{index}",
                status="queued",
                created_at=datetime(2000, 1, 1, index, tzinfo=timezone.utc),
            )
            for index in range(2)
        ]
        session.add_all(lotes)
        session.flush()
        ids = [lote.id for lote in lotes]
        empresa_id = empresa.id
        usuario_id = usuario.id
    return engine, sessions, empresa_id, usuario_id, ids


def _cleanup(engine, sessions, empresa_id, usuario_id):
    with sessions.begin() as session:
        session.execute(AuditEvent.__table__.delete().where(AuditEvent.empresa_id == empresa_id))
        session.execute(LoteImportacaoRazao.__table__.delete().where(
            LoteImportacaoRazao.empresa_id == empresa_id
        ))
        session.execute(Usuario.__table__.delete().where(Usuario.id == usuario_id))
        session.execute(Empresa.__table__.delete().where(Empresa.id == empresa_id))
    engine.dispose()


def test_two_workers_claim_distinct_jobs_with_skip_locked():
    engine, sessions, empresa_id, usuario_id, ids = _context()
    processor = lambda *_: JobResult(0, 0, 0, 0, {"totals_by_code": {}})
    workers = [
        RazaoWorker(sessions, FakeStorage(), processor, worker_id=f"worker-{index}")
        for index in range(2)
    ]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda worker: worker.claim_next(), workers))

        assert {claim.lote_id for claim in claims} == set(ids)
        assert len({claim.lease_token for claim in claims}) == 2
    finally:
        _cleanup(engine, sessions, empresa_id, usuario_id)


def test_heartbeat_uses_independent_transaction_and_lost_owner_cannot_commit():
    engine, sessions, empresa_id, usuario_id, ids = _context()
    target_id = ids[0]
    worker = None

    def process(session, claim, _stream, _progress):
        session.add(
            WarningImportacaoRazao(
                lote_id=claim.lote_id, linha=1, codigo="synthetic",
                mensagem="Aviso sintético.", detalhes={},
            )
        )
        session.flush()
        assert worker.renew_lease(claim) is True
        with sessions.begin() as other:
            other.execute(
                update(LoteImportacaoRazao)
                .where(LoteImportacaoRazao.id == claim.lote_id)
                .values(lease_token=str(uuid4()), heartbeat_at=datetime.now(timezone.utc))
            )
        return JobResult(1, 1, 0, 1, {"totals_by_code": {"synthetic": 1}})

    worker = RazaoWorker(sessions, FakeStorage(), process, worker_id="worker-original")
    try:
        with pytest.raises(LeaseLost):
            worker.run_once()
        with sessions() as session:
            assert session.scalar(
                select(WarningImportacaoRazao).where(WarningImportacaoRazao.lote_id == target_id)
            ) is None
            assert session.get(LoteImportacaoRazao, target_id).status == "processing"
    finally:
        _cleanup(engine, sessions, empresa_id, usuario_id)
