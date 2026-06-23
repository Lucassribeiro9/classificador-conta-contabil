from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    Empresa,
    LancamentoRazaoNormalizado,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Transacao,
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
        nome_empresa="Empresa Operacional LTDA",
        api_key="api-key-operacional",
        cnpj_cpf="11222333000144",
        cod_dominio=1122,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Movimentos",
        login="operador.movimentos",
        email="operador.movimentos@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def test_persiste_lote_e_movimento_operacional_sem_criar_razao_ou_transacao(session):
    empresa = _empresa()
    usuario = _usuario()
    session.add_all([empresa, usuario])
    session.flush()

    lote = LoteImportacaoMovimentoOperacional(
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        original_filename="modelo_movimentos_operacionais_classificacao.xlsx",
        file_hash="sha256:fixture-operacional",
        status="completed_with_warnings",
        total_linhas=2,
        total_importadas=1,
        total_invalidas=1,
        warnings_metadata={"warnings": [{"linha": 2, "mensagem": "em revisao"}]},
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=date(2026, 1, 31),
        cnpj_cpf_arquivo="11222333000144",
        codigo_dominio_arquivo="1122",
    )
    session.add(lote)
    session.flush()

    movimento = MovimentoOperacionalImportado(
        lote_id=lote.id,
        empresa_id=empresa.id,
        data=date(2026, 1, 2),
        conta_financeira=10046,
        historico="Recebimento cliente",
        historico_normalizado="recebimento cliente",
        valor_original=Decimal("3660.15"),
        valor_absoluto=Decimal("3660.15"),
        direcao="entrada",
        tipo_movimento="entrada",
        documento="OFX-0001",
        observacao="Contrapartida conhecida pelo contador",
        contrapartida_informada=10722,
        contrapartida_sugerida=10722,
        contrapartida_final=None,
        confidence_sugerida=0.86,
        status="pre_classificado",
        elegivel_treino=False,
        mensagens_validacao=["aguardando aprovacao humana"],
        conta_debito=None,
        conta_credito=None,
    )
    session.add(movimento)
    session.commit()

    lote_persistido = session.query(LoteImportacaoMovimentoOperacional).one()
    movimento_persistido = session.query(MovimentoOperacionalImportado).one()

    assert lote_persistido.empresa_id == empresa.id
    assert lote_persistido.usuario_id == usuario.id
    assert lote_persistido.periodo_inicio == date(2026, 1, 1)
    assert lote_persistido.periodo_fim == date(2026, 1, 31)
    assert lote_persistido.cnpj_cpf_arquivo == "11222333000144"
    assert lote_persistido.codigo_dominio_arquivo == "1122"
    assert lote_persistido.movimentos == [movimento_persistido]

    assert movimento_persistido.lote_id == lote_persistido.id
    assert movimento_persistido.empresa_id == empresa.id
    assert movimento_persistido.conta_financeira == 10046
    assert movimento_persistido.contrapartida_informada == 10722
    assert movimento_persistido.contrapartida_sugerida == 10722
    assert movimento_persistido.contrapartida_final is None
    assert movimento_persistido.conta_debito is None
    assert movimento_persistido.conta_credito is None
    assert movimento_persistido.elegivel_treino is False
    assert movimento_persistido.mensagens_validacao == [
        "aguardando aprovacao humana"
    ]
    assert movimento_persistido.lote == lote_persistido
    assert movimento_persistido.empresa == empresa

    assert session.query(Transacao).count() == 0
    assert session.query(LancamentoRazaoNormalizado).count() == 0
