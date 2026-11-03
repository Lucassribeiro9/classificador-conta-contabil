"""Eligibility and reproducibility of the company training dataset."""

from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database import Base
from core.dataset_builder import build_dataset_treino_contrapartida
from core.models import ContaContabilEmpresa, FeedbackClassificacao, LoteImportacaoRazao, PlanoContasSnapshotEntry
from core.plano_contas_snapshots import importar_snapshot, selecionar_snapshot
from core.review_items import claim_review_item, create_review_item, dismiss_review_item, resolve_review_item
from core.razao_aliases import confirmar_alias_razao
from tests.test_dataset_builder_contract import (
    _conta,
    _empresa,
    _lancamento,
    _lote_movimentos,
    _movimento,
    _usuario,
)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seed_razao(session):
    empresa = _empresa()
    lote = LoteImportacaoRazao(
        empresa=empresa,
        usuario=_usuario(),
        original_filename="razao-sem-snapshot.xlsx",
        file_hash="sha256:sem-snapshot",
        status="completed",
    )
    session.add_all([
        _conta(10046, is_financial_origin=True),
        _conta(50057, is_financial_origin=False),
        _lancamento(lote, empresa, data=date(2026, 1, 15), linha_original=1),
    ])
    session.commit()
    return empresa, lote


def _snapshot(session, empresa):
    snapshot = importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {"codigo": 10046, "classificacao": "1.1", "nome": "Banco", "tipo": "A", "grau": 2},
            {"codigo": 50057, "classificacao": "2.1", "nome": "Cliente", "tipo": "A", "grau": 2},
        ],
        vigencia=date(2026, 1, 1),
        origem="teste-dataset",
    ).snapshot
    financial = session.scalar(select(ContaContabilEmpresa).where(
        ContaContabilEmpresa.empresa_id == empresa.id,
        ContaContabilEmpresa.codigo == 10046,
    ))
    financial.is_financial_origin = True
    return snapshot


def test_razao_without_temporal_snapshot_is_excluded(session):
    empresa, lote = _seed_razao(session)

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.metadata["total_descartes_razao"] == 1
    assert dataset.manifesto["exclusions"] == [
        {"type": "razao", "id": lote.lancamentos[0].id, "reason": "snapshot_missing"}
    ]


def test_razao_with_valid_snapshot_is_included(session):
    empresa, _ = _seed_razao(session)
    _snapshot(session, empresa)
    session.commit()

    selected = selecionar_snapshot(session, empresa_id=empresa.id, competencia=date(2026, 1, 15))
    assert selected is not None
    assert set(session.scalars(select(PlanoContasSnapshotEntry.codigo).where(PlanoContasSnapshotEntry.snapshot_id == selected.id)).all()) == {10046, 50057}

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == [{
        "features": "recebimento cliente origem_10046 direcao_credito",
        "target_conta_contrapartida": 50057,
    }]


def test_each_composition_persists_a_reconstructible_manifest(session):
    from core.dataset_builder import reconstruct_dataset_from_manifest

    empresa, _ = _seed_razao(session)
    snapshot = _snapshot(session, empresa)
    session.commit()

    first = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    second = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    session.commit()

    assert first.manifesto["id"] != second.manifesto["id"]
    assert first.manifesto["hash"] == second.manifesto["hash"]
    assert first.manifesto["snapshots"] == [snapshot.id]
    assert first.manifesto["snapshot_hashes"] == [
        {"id": snapshot.id, "hash": snapshot.content_hash}
    ]
    assert reconstruct_dataset_from_manifest(
        session, empresa_id=empresa.id, manifest_id=first.manifesto["id"]
    ) == first.linhas


def test_approved_movement_without_temporal_snapshot_is_excluded(session):
    empresa = _empresa()
    movimento = _movimento(_lote_movimentos(empresa), empresa)
    session.add_all([
        _conta(10046, is_financial_origin=True),
        _conta(50057, is_financial_origin=False),
        movimento,
    ])
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.metadata["total_descartes_movimentos"] == 1


def test_critical_review_blocks_razao_until_human_resolution(session):
    empresa, lote = _seed_razao(session)
    _snapshot(session, empresa)
    session.commit()
    user = session.scalar(select(LoteImportacaoRazao).where(LoteImportacaoRazao.id == lote.id)).usuario
    item = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="razao_semantic_divergence",
        grouping_key="test:semantic",
        summary="Divergência semântica",
        criticality="critical",
        evidence=[{"source_type": "razao_line", "source_id": f"{lote.id}:1", "summary": "Linha 1"}],
    )
    session.commit()

    blocked = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    assert blocked.linhas == []

    claim_review_item(session, empresa_id=empresa.id, item_id=item.id, user_id=user.id)
    resolve_review_item(session, empresa_id=empresa.id, item_id=item.id, user_id=user.id, reason="Conta conferida")
    restored = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    session.commit()

    assert len(restored.linhas) == 1
    assert restored.manifesto["hash"] != blocked.manifesto["hash"]


def test_approved_movement_with_valid_snapshot_is_included(session):
    empresa = _empresa()
    movimento = _movimento(_lote_movimentos(empresa), empresa)
    session.add_all([
        _conta(10046, is_financial_origin=True),
        _conta(50057, is_financial_origin=False),
        movimento,
    ])
    session.commit()
    snapshot = _snapshot(session, empresa)
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert len(dataset.linhas) == 1
    assert dataset.manifesto["snapshots"] == [snapshot.id]


def test_feedback_change_is_tracked_even_when_target_stays_the_same(session):
    empresa, lote = _seed_razao(session)
    _snapshot(session, empresa)
    session.commit()
    first = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    session.add(FeedbackClassificacao(
        empresa_id=empresa.id,
        lancamento_id=lote.lancamentos[0].id,
        conta_sugerida=50057,
        conta_final=50057,
        usuario_id=lote.usuario_id,
    ))
    session.flush()

    second = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert first.linhas == second.linhas
    assert first.manifesto["hash"] != second.manifesto["hash"]


def test_confirmed_razao_alias_is_valid_only_in_its_snapshot(session):
    empresa, lote = _seed_razao(session)
    snapshot = _snapshot(session, empresa)
    line = lote.lancamentos[0]
    line.conta_origem = 10047
    line.conta_credito = 10047
    session.add(_conta(10047, is_financial_origin=True))
    session.flush()
    item = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="razao_account_unknown",
        grouping_key=f"{snapshot.id}:10047",
        summary="Alias observado",
        criticality="high",
        evidence=[{"source_type": "razao_line", "source_id": f"{lote.id}:1", "summary": "Linha 1"}],
    )
    claim_review_item(session, empresa_id=empresa.id, item_id=item.id, user_id=lote.usuario_id)
    confirmar_alias_razao(
        session,
        empresa_id=empresa.id,
        item_id=item.id,
        target_codigo=10046,
        user_id=lote.usuario_id,
        reason="Equivalência confirmada",
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas[0]["features"].endswith("origem_10047 direcao_credito")


def test_rejected_movement_has_explicit_exclusion_reason(session):
    empresa = _empresa()
    movimento = _movimento(_lote_movimentos(empresa), empresa, status="rejeitado")
    session.add_all([
        _conta(10046, is_financial_origin=True),
        _conta(50057, is_financial_origin=False),
        movimento,
    ])
    session.commit()
    _snapshot(session, empresa)
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.manifesto["exclusions"] == [
        {"type": "movimento", "id": movimento.id, "reason": "rejected"}
    ]


def test_conflicting_snapshot_excludes_razao_instead_of_guessing(session):
    empresa, lote = _seed_razao(session)
    _snapshot(session, empresa)
    importar_snapshot(
        session,
        empresa_id=empresa.id,
        contas=[
            {"codigo": 10046, "classificacao": "1.1", "nome": "Banco revisado", "tipo": "A", "grau": 2},
            {"codigo": 50057, "classificacao": "2.1", "nome": "Cliente", "tipo": "A", "grau": 2},
        ],
        vigencia=date(2026, 1, 1),
        origem="teste-conflito-dataset",
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.manifesto["exclusions"] == [
        {"type": "razao", "id": lote.lancamentos[0].id, "reason": "snapshot_conflict"}
    ]


def test_critical_review_blocks_approved_movement(session):
    empresa = _empresa()
    movimento = _movimento(_lote_movimentos(empresa), empresa)
    session.add_all([
        _conta(10046, is_financial_origin=True),
        _conta(50057, is_financial_origin=False),
        movimento,
    ])
    session.commit()
    _snapshot(session, empresa)
    item = create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="movimento_operacional_temporal",
        grouping_key=f"movimento:{movimento.id}",
        summary="Revisão crítica do movimento",
        criticality="critical",
        evidence=[{"source_type": "movimento_operacional", "source_id": str(movimento.id), "summary": "Movimento"}],
    )
    session.commit()

    dataset = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert dataset.linhas == []
    assert dataset.manifesto["exclusions"] == [
        {"type": "movimento", "id": movimento.id, "reason": "critical_review_unresolved"}
    ]

    user_id = movimento.lote.usuario_id
    claim_review_item(session, empresa_id=empresa.id, item_id=item.id, user_id=user_id)
    dismiss_review_item(
        session, empresa_id=empresa.id, item_id=item.id, user_id=user_id,
        reason="Registro descartado pela revisão",
    )
    after_dismissal = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert after_dismissal.linhas == []
    assert after_dismissal.manifesto["hash"] != dataset.manifesto["hash"]


def test_unrelated_review_does_not_change_dataset_hash(session):
    empresa, _ = _seed_razao(session)
    _snapshot(session, empresa)
    session.commit()
    first = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)
    create_review_item(
        session,
        empresa_id=empresa.id,
        source_type="movimento_operacional_temporal",
        grouping_key="movimento:999",
        summary="Outro registro",
        criticality="critical",
        evidence=[{"source_type": "movimento_operacional", "source_id": "999", "summary": "Outro movimento"}],
    )

    second = build_dataset_treino_contrapartida(session, empresa_id=empresa.id)

    assert second.manifesto["hash"] == first.manifesto["hash"]
