from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    Empresa,
    FechamentoRazaoMensal,
    LancamentoRazaoNormalizado,
    LoteImportacaoRazao,
    Usuario,
)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _empresa() -> Empresa:
    return Empresa(
        nome_empresa="Empresa Razao LTDA",
        cnpj_cpf="55666777000188",
        api_key="api-key-razao",
        cod_dominio=7701,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Razao",
        login="operador.razao",
        email="operador.razao@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def test_lote_importacao_razao_can_be_persisted_with_file_status_counters_and_metadata(
    session,
):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed_with_warnings",
        total_linhas=10,
        total_importadas=8,
        total_invalidas=2,
        warnings_metadata={
            "warnings": [
                {"linha": 12, "motivo": "contrapartida ausente"},
            ]
        },
    )

    session.add(lote)
    session.commit()

    saved = session.query(LoteImportacaoRazao).one()
    assert saved.empresa.cnpj_cpf == "55666777000188"
    assert saved.usuario.login == "operador.razao"
    assert saved.original_filename == "razao-janeiro.xlsx"
    assert saved.file_hash == "sha256:abc123"
    assert saved.status == "completed_with_warnings"
    assert saved.total_linhas == 10
    assert saved.total_importadas == 8
    assert saved.total_invalidas == 2
    assert saved.warnings_metadata["warnings"][0]["linha"] == 12
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


def test_lancamento_razao_normalizado_can_be_persisted_with_lote_and_company(session):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    lancamento = LancamentoRazaoNormalizado(
        lote=lote,
        empresa=lote.empresa,
        numero_lancamento="12345",
        data=date(2026, 1, 15),
        conta_origem=10046,
        conta_contrapartida=50057,
        conta_debito=50057,
        conta_credito=10046,
        direcao="credito",
        historico="Recebimento cliente",
        historico_normalizado="recebimento cliente",
        valor=Decimal("2500.00"),
    )

    session.add(lancamento)
    session.commit()

    saved = session.query(LancamentoRazaoNormalizado).one()
    assert saved.lote.original_filename == "razao-janeiro.xlsx"
    assert saved.empresa.cnpj_cpf == "55666777000188"
    assert saved.numero_lancamento == "12345"
    assert saved.data == date(2026, 1, 15)
    assert saved.conta_origem == 10046
    assert saved.conta_contrapartida == 50057
    assert saved.conta_debito == 50057
    assert saved.conta_credito == 10046
    assert saved.direcao == "credito"
    assert saved.historico == "Recebimento cliente"
    assert saved.historico_normalizado == "recebimento cliente"
    assert saved.valor == Decimal("2500.00")
    assert isinstance(saved.created_at, datetime)


def test_lancamento_razao_normalizado_persiste_saldos_observados(session):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    lancamento = LancamentoRazaoNormalizado(
        lote=lote,
        empresa=lote.empresa,
        numero_lancamento="12345",
        data=date(2026, 1, 15),
        conta_origem=10046,
        conta_contrapartida=50057,
        conta_debito=50057,
        conta_credito=10046,
        direcao="credito",
        historico="Recebimento cliente",
        historico_normalizado="recebimento cliente",
        valor=Decimal("2500.00"),
        saldo_anterior_original="1.000,00D",
        saldo_anterior_decimal=Decimal("1000.00"),
        saldo_anterior_natureza="D",
        saldo_original="1.250,00C",
        saldo_decimal=Decimal("1250.00"),
        saldo_natureza="C",
        saldo_exercicio_original="2.500,00C",
        saldo_exercicio_decimal=Decimal("2500.00"),
        saldo_exercicio_natureza="C",
    )

    session.add(lancamento)
    session.commit()

    saved = session.query(LancamentoRazaoNormalizado).one()
    assert saved.saldo_anterior_original == "1.000,00D"
    assert saved.saldo_anterior_decimal == Decimal("1000.00")
    assert saved.saldo_anterior_natureza == "D"
    assert saved.saldo_original == "1.250,00C"
    assert saved.saldo_decimal == Decimal("1250.00")
    assert saved.saldo_natureza == "C"
    assert saved.saldo_exercicio_original == "2.500,00C"
    assert saved.saldo_exercicio_decimal == Decimal("2500.00")
    assert saved.saldo_exercicio_natureza == "C"


def test_fechamento_razao_mensal_isolado_por_empresa_conta_mes_e_lote(session):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    fechamento = FechamentoRazaoMensal(
        lote=lote,
        empresa=lote.empresa,
        conta_codigo=10046,
        ano=2026,
        mes=1,
        saldo_observado_original="850,00D",
        saldo_observado_decimal=Decimal("850.00"),
        saldo_observado_natureza="D",
        saldo_observado_fonte="saldo_exercicio",
        saldo_calculado_decimal=Decimal("850.00"),
        warnings_saldo=[],
    )

    session.add(fechamento)
    session.commit()

    saved = session.query(FechamentoRazaoMensal).one()
    assert saved.lote.original_filename == "razao-janeiro.xlsx"
    assert saved.empresa.cnpj_cpf == "55666777000188"
    assert saved.conta_codigo == 10046
    assert saved.ano == 2026
    assert saved.mes == 1
    assert saved.saldo_observado_original == "850,00D"
    assert saved.saldo_observado_decimal == Decimal("850.00")
    assert saved.saldo_observado_natureza == "D"
    assert saved.saldo_observado_fonte == "saldo_exercicio"
    assert saved.saldo_calculado_decimal == Decimal("850.00")
    assert saved.warnings_saldo == []
    assert isinstance(saved.created_at, datetime)
    assert isinstance(saved.updated_at, datetime)


def test_lote_importacao_razao_exposes_related_monthly_closings(session):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    lote.fechamentos_mensais.append(
        FechamentoRazaoMensal(
            empresa=lote.empresa,
            conta_codigo=10046,
            ano=2026,
            mes=1,
            saldo_observado_original="850,00D",
            saldo_observado_decimal=Decimal("850.00"),
            saldo_observado_natureza="D",
            saldo_observado_fonte="saldo_exercicio",
            saldo_calculado_decimal=Decimal("850.00"),
            warnings_saldo=[],
        )
    )

    session.add(lote)
    session.commit()

    saved = session.query(LoteImportacaoRazao).one()
    assert len(saved.fechamentos_mensais) == 1
    assert saved.fechamentos_mensais[0].conta_codigo == 10046


def test_migration_persiste_saldos_e_fechamentos_mensais_do_razao():
    migration_files = list(
        Path("alembic/versions").glob("*_add_razao_balance_closings.py")
    )
    assert len(migration_files) == 1
    migration = migration_files[0].read_text()

    for column_name in (
        "saldo_anterior_original",
        "saldo_anterior_decimal",
        "saldo_anterior_natureza",
        "saldo_original",
        "saldo_decimal",
        "saldo_natureza",
        "saldo_exercicio_original",
        "saldo_exercicio_decimal",
        "saldo_exercicio_natureza",
    ):
        assert f'"{column_name}"' in migration

    assert '"fechamentos_razao_mensais"' in migration
    assert "uq_fechamentos_razao_mensais_empresa_conta_mes_lote" in migration
    assert "Numeric(precision=14, scale=2)" in migration
    assert "def downgrade" in migration


def test_lote_importacao_razao_exposes_related_normalized_entries(session):
    lote = LoteImportacaoRazao(
        empresa=_empresa(),
        usuario=_usuario(),
        original_filename="razao-janeiro.xlsx",
        file_hash="sha256:abc123",
        status="completed",
    )
    lote.lancamentos.append(
        LancamentoRazaoNormalizado(
            empresa=lote.empresa,
            numero_lancamento="12345",
            data=date(2026, 1, 15),
            conta_origem=10046,
            conta_contrapartida=50057,
            conta_debito=50057,
            conta_credito=10046,
            direcao="credito",
            historico="Recebimento cliente",
            historico_normalizado="recebimento cliente",
            valor=Decimal("2500.00"),
        )
    )

    session.add(lote)
    session.commit()

    saved = session.query(LoteImportacaoRazao).one()
    assert len(saved.lancamentos) == 1
    assert saved.lancamentos[0].conta_origem == 10046
