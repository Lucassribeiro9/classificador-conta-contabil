from datetime import date
from decimal import Decimal
from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.dataset_builder import DatasetTreinoContrapartida
from core.ml_engine import ClassificadorContabil
from core.models import (
    AuditEvent,
    ContaContabilEmpresa,
    DatasetManifest,
    Empresa,
    LoteImportacaoMovimentoOperacional,
    MovimentoOperacionalImportado,
    ModelVersion,
    PlanoContasSnapshot,
    ReviewItem,
    Usuario,
)
from core.movimentos_operacionais_classification import (
    _snapshot_for_undated_movement,
    classificar_movimentos_operacionais_pendentes,
)
from core.plano_contas_snapshots import importar_snapshot
from core.review_items import create_review_item


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


def _lote(
    empresa: Empresa,
    usuario: Usuario,
    *,
    layout_version: str = "operacional_valor_legado_v1",
) -> LoteImportacaoMovimentoOperacional:
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
        layout_version=layout_version,
    )


def _movimento(
    lote: LoteImportacaoMovimentoOperacional,
    empresa: Empresa,
    *,
    status: str,
    historico_normalizado: str,
    tipo_movimento: str | None = "saida",
    valor_original: Decimal = Decimal("-250.75"),
    valor_absoluto: Decimal = Decimal("250.75"),
    direcao: str = "credito",
    saldo_observado_original: str | None = None,
    saldo_observado_decimal: Decimal | None = None,
    saldo_calculado_decimal: Decimal | None = None,
    warnings_saldo: list[str] | None = None,
) -> MovimentoOperacionalImportado:
    return MovimentoOperacionalImportado(
        lote=lote,
        empresa=empresa,
        data=date(2026, 1, 2),
        conta_financeira=10046,
        historico=f"{historico_normalizado} bruto",
        historico_normalizado=historico_normalizado,
        valor_original=valor_original,
        valor_absoluto=valor_absoluto,
        direcao=direcao,
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
        saldo_observado_original=saldo_observado_original,
        saldo_observado_decimal=saldo_observado_decimal,
        saldo_calculado_decimal=saldo_calculado_decimal,
        warnings_saldo=warnings_saldo or [],
    )


def _train_razao_dataset_model(
    db, tmp_path, empresa_id: int, *, threshold: float = 0.70,
    manifest_content: dict | None = None,
) -> None:
    dataset = DatasetTreinoContrapartida(
        linhas=[
            {
                "features": f"pagamento fornecedor {i} origem_10046 direcao_credito tipo_saida",
                "target_conta_contrapartida": 20001,
            }
            for i in range(6)
        ]
        + [
            {
                "features": f"recebimento cliente {i} origem_10046 direcao_debito tipo_entrada",
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
    manifest = DatasetManifest(
        empresa_id=empresa_id, content_hash="a" * 64,
        content=manifest_content or {},
    )
    db.add(manifest)
    db.flush()
    version = ModelVersion(
        empresa_id=empresa_id, manifest_id=manifest.id, status="active",
        threshold=threshold, artifact_path="", artifact_sha256="",
        metrics={}, evaluation={}, critical_classes=[],
    )
    db.add(version)
    db.flush()
    relative_path = f"empresa_{empresa_id}/model_{version.id}.joblib"
    artifact = tmp_path / relative_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(engine._model_path_for_company(empresa_id).read_bytes())
    version.artifact_path = relative_path
    version.artifact_sha256 = sha256(artifact.read_bytes()).hexdigest()
    db.query(AuditEvent).delete()
    db.commit()


def _import_classification_snapshot(session, empresa: Empresa) -> None:
    session.flush()
    importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {
                "codigo": code,
                "classificacao": f"1.{index}",
                "nome": f"Conta {code}",
                "tipo": "A",
                "grau": 2,
            }
            for index, code in enumerate((10046, 20001, 30001), start=1)
        ],
        vigencia=date(2026, 1, 1),
        origem="snapshot-classificacao-teste",
    )


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
    _import_classification_snapshot(session, empresa)
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
    assert pendente.ml_suggestion_context["model_version_id"] is not None
    assert pendente.ml_suggestion_context["snapshot_id"] is not None
    assert pendente.ml_suggestion_context["context_source"] == "movement_date"
    assert ja_revisao.contrapartida_sugerida is None
    assert ja_revisao.status == "revisao"

    event = (
        session.query(AuditEvent)
        .filter(AuditEvent.event_type == "operational_movements.classified")
        .one()
    )
    assert event.event_type == "operational_movements.classified"
    assert event.empresa_id == empresa.id
    assert event.metadata_json["total_processado"] == 1
    assert event.metadata_json["total_sugerido"] == 1
    assert event.metadata_json["total_revisao"] == 0
    assert "pagamento fornecedor" not in str(event.metadata_json)
    assert "DOC-SENSIVEL-001" not in str(event.metadata_json)
    temporal_event = (
        session.query(AuditEvent)
        .filter(
            AuditEvent.event_type == "operational_movements.temporal_context_checked"
        )
        .one()
    )
    assert temporal_event.metadata_json["context_source"] == "movement_date"
    assert temporal_event.metadata_json["snapshot_id"] is not None
    assert "pagamento fornecedor" not in str(temporal_event.metadata_json)


def test_classificar_movimentos_usa_contrato_interno_independente_do_layout(
    session,
    tmp_path,
):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(
        empresa,
        usuario,
        layout_version="operacional_debito_credito_saldo_v1",
    )
    pendente = _movimento(
        lote,
        empresa,
        status="pendente",
        historico_normalizado="recebimento cliente boleto",
        tipo_movimento="entrada",
        valor_original=Decimal("1500.00"),
        valor_absoluto=Decimal("1500.00"),
        direcao="debito",
        saldo_observado_original="1500",
        saldo_observado_decimal=Decimal("1500.00"),
        saldo_calculado_decimal=Decimal("1500.00"),
        warnings_saldo=[],
    )
    session.add(pendente)
    _import_classification_snapshot(session, empresa)
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id)

    result = classificar_movimentos_operacionais_pendentes(
        session,
        empresa_id=empresa.id,
        model_dir=tmp_path,
    )

    session.refresh(pendente)
    assert result["quantidade_processada"] == 1
    assert pendente.status == "sugerido"
    assert pendente.contrapartida_sugerida in {20001, 30001}
    assert pendente.valor_original == Decimal("1500.00")
    assert pendente.valor_absoluto == Decimal("1500.00")
    assert pendente.direcao == "debito"


def test_previsao_abaixo_do_threshold_abstem_e_cria_pendencia(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    movimento = _movimento(
        lote, empresa, status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    _import_classification_snapshot(session, empresa)
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id, threshold=1.0)
    version = session.query(ModelVersion).one()

    result = classificar_movimentos_operacionais_pendentes(
        session, empresa_id=empresa.id, model_dir=tmp_path,
    )

    session.refresh(movimento)
    assert result["total_revisao"] == 1
    assert movimento.status == "revisao"
    assert movimento.contrapartida_sugerida is None
    assert movimento.contrapartida_final is None
    assert movimento.ml_suggestion_context["model_version_id"] == version.id
    assert movimento.ml_suggestion_context["abstention_reason"] == "below_threshold"
    assert session.query(ReviewItem).filter_by(
        source_type="movimento_operacional_ml",
        grouping_key=f"movimento:{movimento.id}",
    ).one().status == "pending"


def test_artefato_legado_sem_versao_ativa_nao_gera_sugestao(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    movimento = _movimento(
        lote, empresa, status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    _import_classification_snapshot(session, empresa)
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id)
    session.query(ModelVersion).delete()
    session.commit()

    result = classificar_movimentos_operacionais_pendentes(
        session, empresa_id=empresa.id, model_dir=tmp_path,
    )

    session.refresh(movimento)
    assert result["total_revisao"] == 1
    assert movimento.status == "revisao"
    assert movimento.contrapartida_sugerida is None
    assert movimento.ml_suggestion_context["abstention_reason"] == "model_version_missing"
    assert session.query(ReviewItem).filter_by(
        source_type="movimento_operacional_ml",
        grouping_key=f"movimento:{movimento.id}",
    ).count() == 1


def test_pendencia_critica_aberta_impede_sugestao(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    movimento = _movimento(
        lote, empresa, status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    _import_classification_snapshot(session, empresa)
    session.flush()
    create_review_item(
        session, empresa_id=empresa.id,
        source_type="movimento_operacional", grouping_key=f"critico:{movimento.id}",
        summary="Pendência crítica sintética", criticality="critical",
        evidence=[{
            "source_type": "movimento_operacional",
            "source_id": str(movimento.id),
            "summary": "Bloqueio sintético",
        }],
    )
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id)

    result = classificar_movimentos_operacionais_pendentes(
        session, empresa_id=empresa.id, model_dir=tmp_path,
    )

    session.refresh(movimento)
    assert result["total_revisao"] == 1
    assert movimento.contrapartida_sugerida is None
    assert movimento.ml_suggestion_context["abstention_reason"] == "critical_review_unresolved"
    assert session.query(ReviewItem).filter_by(
        source_type="movimento_operacional_ml",
        grouping_key=f"movimento:{movimento.id}",
    ).count() == 1


def test_sugestao_mostra_apenas_exemplos_elegiveis_da_empresa(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    pendente = _movimento(
        lote, empresa, status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    elegiveis = [
        _movimento(lote, empresa, status="aprovado", historico_normalizado=f"exemplo elegivel {code}")
        for code in (20001, 30001)
    ]
    for example, code in zip(elegiveis, (20001, 30001)):
        example.contrapartida_final = code
        example.elegivel_treino = True
        example.conta_debito = 10046
        example.conta_credito = code
    incompletos = [
        _movimento(lote, empresa, status="aprovado", historico_normalizado=f"exemplo incompleto {code}")
        for code in (20001, 30001)
    ]
    for example, code in zip(incompletos, (20001, 30001)):
        example.contrapartida_final = code
        example.elegivel_treino = True
    inelegivel = _movimento(
        lote, empresa, status="rejeitado",
        historico_normalizado="exemplo rejeitado",
    )
    inelegivel.contrapartida_final = 20001
    inelegivel.elegivel_treino = True
    outra_empresa = Empresa(
        nome_empresa="Outra Empresa LTDA", cnpj_cpf="22333444000155",
        api_key="outra-api-key", cod_dominio=4456,
    )
    outro_lote = _lote(outra_empresa, usuario)
    outro_exemplo = _movimento(
        outro_lote, outra_empresa, status="aprovado",
        historico_normalizado="exemplo outra empresa",
    )
    outro_exemplo.contrapartida_final = 20001
    outro_exemplo.elegivel_treino = True
    session.add_all([pendente, *elegiveis, *incompletos, inelegivel, outro_exemplo])
    _import_classification_snapshot(session, empresa)
    session.flush()
    session.query(ContaContabilEmpresa).filter_by(
        empresa_id=empresa.id, codigo=10046,
    ).one().is_financial_origin = True
    session.commit()
    _train_razao_dataset_model(session, tmp_path, empresa.id)

    classificar_movimentos_operacionais_pendentes(
        session, empresa_id=empresa.id, model_dir=tmp_path,
    )

    session.refresh(pendente)
    examples = pendente.ml_suggestion_context["historical_examples"]
    assert len(examples) == 1
    assert examples[0]["movement_id"] in {item.id for item in elegiveis}
    assert examples[0]["account_code"] == pendente.contrapartida_sugerida
    assert inelegivel.id not in {item["movement_id"] for item in examples}
    assert not {item.id for item in incompletos} & {item["movement_id"] for item in examples}
    assert outro_exemplo.id not in {item["movement_id"] for item in examples}


def test_sugestao_inclui_exemplo_elegivel_do_manifesto_do_razao(session, tmp_path):
    empresa = _empresa()
    usuario = _usuario()
    movimento = _movimento(
        _lote(empresa, usuario), empresa, status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    _import_classification_snapshot(session, empresa)
    session.flush()
    snapshot_id = session.query(PlanoContasSnapshot).filter_by(
        empresa_id=empresa.id,
    ).one().id
    session.commit()
    _train_razao_dataset_model(
        session, tmp_path, empresa.id,
        manifest_content={
            "sources": [
                {"type": "razao", "id": 81, "snapshot_id": snapshot_id},
                {"type": "razao", "id": 82, "snapshot_id": snapshot_id},
            ],
            "rows": [
                {"features": "pagamento fornecedor origem_10046 direcao_credito", "target_conta_contrapartida": 20001},
                {"features": "recebimento cliente origem_10046 direcao_debito", "target_conta_contrapartida": 30001},
            ],
        },
    )

    classificar_movimentos_operacionais_pendentes(
        session, empresa_id=empresa.id, model_dir=tmp_path,
    )

    session.refresh(movimento)
    examples = movimento.ml_suggestion_context["historical_examples"]
    assert len(examples) == 1
    assert examples[0]["source_type"] == "razao"
    assert examples[0]["account_code"] == movimento.contrapartida_sugerida


def test_classificacao_sem_snapshot_abstem_e_cria_revisao_temporal(
    session,
    monkeypatch,
):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    movimento = _movimento(
        lote,
        empresa,
        status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    session.commit()

    class FakeClassifier:
        def __init__(self, _session, model_dir=None):
            pass

        def model_exists_for_company(self, _empresa_id):
            return True

        def classify_operational_movements_from_saved_model(self, **_kwargs):
            return [
                {
                    "contrapartida_sugerida": 20001,
                    "confidence_sugerida": 0.95,
                    "status": "sugerido",
                }
            ]

    monkeypatch.setattr(
        "core.movimentos_operacionais_classification.ClassificadorContabil",
        FakeClassifier,
    )

    result = classificar_movimentos_operacionais_pendentes(
        session,
        empresa_id=empresa.id,
    )

    session.refresh(movimento)
    review = session.query(ReviewItem).one()
    assert result == {
        "empresa_id": empresa.id,
        "quantidade_processada": 1,
        "total_sugerido": 0,
        "total_revisao": 1,
    }
    assert movimento.status == "revisao"
    assert movimento.contrapartida_sugerida is None
    assert review.source_type == "movimento_operacional_temporal"
    assert review.grouping_key == f"movimento:{movimento.id}"
    assert str(movimento.data) in review.summary
    assert review.status == "pending"


def test_classificacao_abstem_quando_conta_financeira_nao_esta_no_snapshot(
    session,
    monkeypatch,
):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    movimento = _movimento(
        lote,
        empresa,
        status="pendente",
        historico_normalizado="pagamento fornecedor aluguel",
    )
    session.add(movimento)
    session.flush()
    importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {
                "codigo": 20001,
                "classificacao": "2.1.01",
                "nome": "Fornecedores",
                "tipo": "A",
                "grau": 3,
            }
        ],
        vigencia=date(2026, 1, 1),
        origem="snapshot-teste",
    )
    session.commit()

    class FakeClassifier:
        def __init__(self, _session, model_dir=None):
            pass

        def model_exists_for_company(self, _empresa_id):
            return True

        def classify_operational_movements_from_saved_model(self, **_kwargs):
            raise AssertionError(
                "Conta financeira fora do snapshot não pode ser classificada"
            )

    monkeypatch.setattr(
        "core.movimentos_operacionais_classification.ClassificadorContabil",
        FakeClassifier,
    )

    result = classificar_movimentos_operacionais_pendentes(
        session,
        empresa_id=empresa.id,
    )

    session.refresh(movimento)
    review = session.query(ReviewItem).one()
    assert result["total_sugerido"] == 0
    assert result["total_revisao"] == 1
    assert movimento.status == "revisao"
    assert movimento.contrapartida_sugerida is None
    assert "conta financeira" in review.summary.lower()


def test_fallback_periodo_lote_so_usa_snapshot_quando_nao_ha_transicao(
    session,
):
    empresa = _empresa()
    usuario = _usuario()
    lote = _lote(empresa, usuario)
    session.add(lote)
    session.flush()
    importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {
                "codigo": code,
                "classificacao": f"1.{index}",
                "nome": f"Conta {code}",
                "tipo": "A",
                "grau": 2,
            }
            for index, code in enumerate((10046, 20001), start=1)
        ],
        vigencia=date(2026, 1, 1),
        origem="snapshot-inicial",
    )
    initial = _snapshot_for_undated_movement(session, empresa.id, lote)
    assert initial is not None

    importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {
                "codigo": code,
                "classificacao": f"2.{index}",
                "nome": f"Conta {code}",
                "tipo": "A",
                "grau": 2,
            }
            for index, code in enumerate((10046, 20001, 30001), start=1)
        ],
        vigencia=date(2026, 1, 15),
        origem="snapshot-transicao",
    )
    assert _snapshot_for_undated_movement(session, empresa.id, lote) is None
