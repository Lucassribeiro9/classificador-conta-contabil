from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.dataset_builder import DatasetTreinoContrapartida
from core.ml_engine import ClassificadorContabil
from core.models import (
    AuditEvent,
    Empresa,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    Usuario,
)
from core.movimentos_operacionais_classification import (
    classificar_movimentos_operacionais_pendentes,
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
        nome_empresa="Empresa Classificacao Movimentos LTDA",
        cnpj_cpf="11222333000144",
        api_key="api-key-classificacao-movimentos",
        cod_dominio=4455,
    )


def _usuario() -> Usuario:
    return Usuario(
        nome="Operador Classificacao",
        login="operador.classificacao.movimentos",
        email="operador.classificacao.movimentos@example.com",
        senha_hash="$argon2id$v=19$hash-de-teste",
        papel="operador",
    )


def _lote(empresa: Empresa, usuario: Usuario) -> LoteImportacaoMovimentoOperacional:
    return LoteImportacaoMovimentoOperacional(
        empresa=empresa,
        usuario=usuario,
        original_filename="movimentos-classificacao.xlsx",
        file_hash="sha256:movimentos-classificacao",
        status="completed",
        total_linhas=3,
        total_importadas=3,
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
    historico_normalizado: str,
    tipo_movimento: str | None = "saida",
) -> MovimentoOperacionalImportado:
    return MovimentoOperacionalImportado(
        lote=lote,
        empresa=empresa,
        data=date(2026, 1, 2),
        conta_financeira=10046,
        historico=f"{historico_normalizado} bruto",
        historico_normalizado=historico_normalizado,
        valor_original=Decimal("-250.75"),
        valor_absoluto=Decimal("250.75"),
        direcao="saida",
        tipo_movimento=tipo_movimento,
        documento="DOC-SENSIVEL-001",
        observacao="Observacao sensivel",
        contrapartida_informada=None,
        contrapartida_sugerida=None,
        contrapartida_final=None,
        confidence_sugerida=None,
        status=status,
        elegivel_treino=False,
        mensagens_validacao=[],
        conta_debito=None,
        conta_credito=None,
    )


def _train_razao_dataset_model(db, tmp_path, empresa_id: int) -> None:
    dataset = DatasetTreinoContrapartida(
        linhas=[
            {
                "features": f"pagamento fornecedor {i} origem_10046 direcao_saida tipo_saida",
                "target_conta_contrapartida": 20001,
            }
            for i in range(6)
        ]
        + [
            {
                "features": f"recebimento cliente {i} origem_10046 direcao_entrada tipo_entrada",
                "target_conta_contrapartida": 30001,
            }
            for i in range(6)
        ],
        metadata={
            "empresa_id": empresa_id,
            "total_linhas": 12,
            "total_descartes": 0,
            "contagem_por_target": {20001: 6, 30001: 6},
            "treinavel": True,
        },
    )
    engine = ClassificadorContabil(db, model_dir=tmp_path)
    assert engine.train_from_dataset(dataset) is True
    db.query(AuditEvent).delete()
    db.commit()


def test_classificar_movimentos_pendentes_persiste_sugestao_e_auditoria(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    pendente = _movimento(
        lote,
        empresa,
        status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    ja_revisao = _movimento(
        lote,
        empresa,
        status="revisao",
        historico_normalizado="transferencia sem contrapartida",
        tipo_movimento="transferencia",
    )
    session.add_all([pendente, ja_revisao])
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id)

    result = classificar_movimentos_operacionais_pendentes(
        session,
        empresa_id=empresa.id,
        model_dir=tmp_path,
    )

    session.refresh(pendente)
    session.refresh(ja_revisao)
    assert result == {
        "empresa_id": empresa.id,
        "quantidade_processada": 1,
        "total_sugerido": 1,
        "total_revisao": 0,
    }
    assert pendente.contrapartida_sugerida in {20001, 30001}
    assert pendente.confidence_sugerida is not None
    assert pendente.status == "sugerido"
    assert pendente.contrapartida_final is None
    assert pendente.conta_debito is None
    assert pendente.conta_credito is None
    assert pendente.elegivel_treino is False
    assert ja_revisao.contrapartida_sugerida is None
    assert ja_revisao.status == "revisao"

    event = session.query(AuditEvent).one()
    assert event.event_type == "operational_movements.classified"
    assert event.empresa_id == empresa.id
    assert event.metadata_json["total_processado"] == 1
    assert event.metadata_json["total_sugerido"] == 1
    assert event.metadata_json["total_revisao"] == 0
    assert "pagamento fornecedor" not in str(event.metadata_json)
    assert "DOC-SENSIVEL-001" not in str(event.metadata_json)
