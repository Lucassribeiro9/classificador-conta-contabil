from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.models import (
    AuditEvent,
    ContaContabil,
    Empresa,
    EmpresaContaContabil,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Usuario,
)
from core.movimentos_operacionais_bulk_approval import (
    aprovar_movimentos_operacionais_em_lote,
)


@pytest.fixture()
def session():
    """Cria banco SQLite isolado para aprovacao em lote."""

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
    """Cria empresa minima para aprovacao em lote."""

    return Empresa(
        nome_empresa="Empresa Bulk Movimentos LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-bulk-movimentos",
        cod_dominio=4455,
    )


def _usuario() -> Usuario:
    """Cria usuario minimo para auditoria da aprovacao."""

    return Usuario(
        nome="Operador Bulk",
        login="operador.bulk",
        email="operador.bulk@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _conta(codigo: int) -> ContaContabil:
    """Cria conta contabil analitica e ativa."""

    return ContaContabil(
        codigo=codigo,
        classificacao=f"1.1.{codigo}",
        nome=f"CONTA {codigo}",
        tipo="A",
        grau=6,
    )


def _vinculo(empresa_id: int, conta_codigo: int) -> EmpresaContaContabil:
    """Cria vinculo entre empresa e conta contabil."""

    return EmpresaContaContabil(
        empresa_id=empresa_id,
        conta_codigo=conta_codigo,
        quantidade_lancamentos=1,
        ultima_utilizacao=date(2026, 1, 1),
    )


def _lote(empresa: Empresa, usuario: Usuario) -> LoteImportacaoMovimentoOperacional:
    """Cria lote operacional para agregar movimentos."""

    return LoteImportacaoMovimentoOperacional(
        empresa=empresa,
        usuario=usuario,
        original_filename="movimentos-bulk.xlsx",
        file_hash="sha256:movimentos-bulk",
        status="completed_with_warnings",
        total_linhas=6,
        total_importadas=6,
        total_invalidas=0,
        warnings_metadata={"warnings": []},
        periodo_inicio=date(2026, 1, 1),
        periodo_fim=date(2026, 1, 31),
        cnpj_cpf_arquivo=empresa.cnpj_cpf,
        codigo_dominio_arquivo=str(empresa.cod_dominio),
    )


def _movimento(
    lote: LoteImportacaoMovimentoOperacional,
    empresa: Empresa,
    *,
    status: str,
    contrapartida_informada: int | None = None,
    contrapartida_sugerida: int | None = None,
    confidence_sugerida: float | None = None,
    mensagens_validacao: list[str] | None = None,
) -> MovimentoOperacionalImportado:
    """Cria movimento operacional com campos comuns ao fluxo de aprovacao."""

    return MovimentoOperacionalImportado(
        lote=lote,
        empresa=empresa,
        data=date(2026, 1, 2),
        conta_financeira=10046,
        historico="Pagamento fornecedor sensivel",
        historico_normalizado="pagamento fornecedor",
        valor_original=Decimal("-250.75"),
        valor_absoluto=Decimal("250.75"),
        direcao="credito",
        tipo_movimento="saida",
        documento="DOC-SENSIVEL-001",
        observacao="Observacao sensivel",
        contrapartida_informada=contrapartida_informada,
        contrapartida_sugerida=contrapartida_sugerida,
        contrapartida_final=None,
        confidence_sugerida=confidence_sugerida,
        status=status,
        elegivel_treino=False,
        mensagens_validacao=mensagens_validacao or [],
        conta_debito=None,
        conta_credito=None,
    )


def test_aprovar_movimentos_em_lote_aprova_elegiveis_e_audita(session):
    """Deve aprovar apenas elegiveis, retornar itens e registrar auditoria."""

    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    session.add_all(
        [
            empresa,
            usuario,
            _conta(10046),
            _conta(20001),
            _conta(30001),
            _conta(40001),
        ]
    )
    session.flush()
    session.add_all(
        [
            _vinculo(empresa.id, 10046),
            _vinculo(empresa.id, 20001),
            _vinculo(empresa.id, 30001),
        ]
    )
    pre_classificado = _movimento(
        lote,
        empresa,
        status="pre_classificado",
        contrapartida_informada=20001,
    )
    sugerido_alta = _movimento(
        lote,
        empresa,
        status="sugerido",
        contrapartida_sugerida=30001,
        confidence_sugerida=0.82,
    )
    em_revisao = _movimento(
        lote,
        empresa,
        status="revisao",
        contrapartida_sugerida=30001,
        confidence_sugerida=0.82,
    )
    baixa_confianca = _movimento(
        lote,
        empresa,
        status="sugerido",
        contrapartida_sugerida=30001,
        confidence_sugerida=0.69,
    )
    contrapartida_nao_vinculada = _movimento(
        lote,
        empresa,
        status="pre_classificado",
        contrapartida_informada=40001,
    )
    session.add_all(
        [
            lote,
            pre_classificado,
            sugerido_alta,
            em_revisao,
            baixa_confianca,
            contrapartida_nao_vinculada,
        ]
    )
    session.commit()

    result = aprovar_movimentos_operacionais_em_lote(
        session,
        empresa_id=empresa.id,
        usuario_id=usuario.id,
        movimento_ids=[
            pre_classificado.id,
            sugerido_alta.id,
            em_revisao.id,
            baixa_confianca.id,
            contrapartida_nao_vinculada.id,
            999999,
        ],
    )

    session.refresh(pre_classificado)
    session.refresh(sugerido_alta)
    session.refresh(em_revisao)
    session.refresh(baixa_confianca)
    session.refresh(contrapartida_nao_vinculada)

    assert result["aprovados"] == [
        {"id": pre_classificado.id, "conta_final": 20001},
        {"id": sugerido_alta.id, "conta_final": 30001},
    ]
    assert result["ignorados"] == [
        {"id": em_revisao.id, "motivo": "movimento_nao_elegivel"},
        {"id": baixa_confianca.id, "motivo": "baixa_confianca"},
        {
            "id": contrapartida_nao_vinculada.id,
            "motivo": "contrapartida_nao_vinculada",
        },
    ]
    assert result["erros"] == [
        {"id": 999999, "erro": "movimento_nao_encontrado"}
    ]
    assert pre_classificado.status == "aprovado"
    assert pre_classificado.contrapartida_final == 20001
    assert pre_classificado.elegivel_treino is True
    assert pre_classificado.conta_debito == 20001
    assert pre_classificado.conta_credito == 10046
    assert sugerido_alta.status == "aprovado"
    assert sugerido_alta.contrapartida_final == 30001
    assert em_revisao.status == "revisao"
    assert baixa_confianca.status == "sugerido"
    assert contrapartida_nao_vinculada.status == "pre_classificado"
    assert (
        session.query(EmpresaContaContabil)
        .filter(EmpresaContaContabil.empresa_id == empresa.id)
        .count()
        == 3
    )

    event = session.query(AuditEvent).one()
    assert event.event_type == "operational_movements.bulk_approved"
    assert event.user_id == usuario.id
    assert event.empresa_id == empresa.id
    assert event.metadata_json == {
        "movimento_ids": [
            pre_classificado.id,
            sugerido_alta.id,
            em_revisao.id,
            baixa_confianca.id,
            contrapartida_nao_vinculada.id,
            999999,
        ],
        "aprovados": [pre_classificado.id, sugerido_alta.id],
        "ignorados": [
            em_revisao.id,
            baixa_confianca.id,
            contrapartida_nao_vinculada.id,
        ],
        "erros": [999999],
        "total_aprovados": 2,
        "total_ignorados": 3,
        "total_erros": 1,
    }
    assert "Pagamento fornecedor sensivel" not in str(event.metadata_json)
    assert "DOC-SENSIVEL-001" not in str(event.metadata_json)
