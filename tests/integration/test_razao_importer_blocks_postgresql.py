"""Instrumentação SQL do importador em blocos contra PostgreSQL real."""

from math import ceil
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from core.models import ContaContabil, Empresa, LancamentoRazaoNormalizado, Usuario
from core.razao_importer import import_razao


pytestmark = pytest.mark.integration_postgres


def _parsed_line(numero: int) -> dict:
    return {
        "bloco_id": "bloco:postgres",
        "data": "2026-01-02",
        "numero": str(numero),
        "historico": f"Lançamento sintético {numero}",
        "conta_origem": "10046",
        "contrapartida": "20001",
        "debito": "10.00",
        "credito": None,
    }


def test_sql_statements_scale_with_blocks_instead_of_rows(tmp_path, monkeypatch):
    """Pré-cargas são constantes e INSERTs de lançamentos seguem os blocos."""
    from core import razao_importer

    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url and make_url(database_url).get_backend_name() == "postgresql"
    engine = create_engine(database_url)
    session = sessionmaker(bind=engine)()
    suffix = uuid4().hex[:10]
    empresa = Empresa(
        nome_empresa=f"Empresa blocos {suffix}",
        cnpj_cpf=str(int(suffix, 16) % 10**14).zfill(14),
        api_key=f"api-{suffix}",
        cod_dominio=int(suffix, 16) % 2_000_000_000,
    )
    usuario = Usuario(
        nome="Operador blocos",
        login=f"blocos-{suffix}",
        email=f"blocos-{suffix}@example.com",
        senha_hash="synthetic",
        papel="operador",
    )
    session.add_all(
        [
            empresa,
            usuario,
            ContaContabil(
                codigo=10046,
                classificacao="1.1.10046",
                nome="CONTA 10046",
                tipo="A",
                grau=6,
            ),
            ContaContabil(
                codigo=20001,
                classificacao="1.1.20001",
                nome="CONTA 20001",
                tipo="A",
                grau=6,
            ),
        ]
    )
    session.flush()
    row_count = 40
    block_size = 7
    parsed = [_parsed_line(index) for index in range(1, row_count + 1)]
    monkeypatch.setattr(
        razao_importer,
        "_parse_lancamentos_and_validate_company",
        lambda *_: parsed,
    )
    path = Path(tmp_path) / "synthetic-postgresql.xlsx"
    path.write_bytes(b"synthetic-postgresql")
    statements: list[tuple[str, bool]] = []

    def capture(_conn, _cursor, statement, _params, context, _many):
        statements.append((statement, bool(context.executemany)))

    event.listen(engine, "before_cursor_execute", capture)
    try:
        result = import_razao(
            session,
            path,
            empresa_id=empresa.id,
            usuario_id=usuario.id,
            original_filename="synthetic-postgresql.xlsx",
            block_size=block_size,
        )

        catalog_selects = [sql for sql, _ in statements if "FROM contas_contabeis" in sql]
        link_selects = [sql for sql, _ in statements if "FROM empresa_contas_contabeis" in sql]
        entry_inserts = [
            (sql, many)
            for sql, many in statements
            if "INSERT INTO lancamentos_razao_normalizados" in sql
        ]
        assert len(catalog_selects) == 1
        assert len(link_selects) == 1
        assert len(entry_inserts) == ceil(row_count / block_size)
        assert all(many for _, many in entry_inserts)
        assert result.total_importadas == row_count
        assert session.query(LancamentoRazaoNormalizado).count() == row_count
    finally:
        session.rollback()
        session.close()
        engine.dispose()
