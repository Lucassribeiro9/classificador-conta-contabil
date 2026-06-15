from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    Empresa,
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
