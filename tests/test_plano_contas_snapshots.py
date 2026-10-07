"""Contrato de importação e seleção temporal do plano por empresa."""

from datetime import date

from core.models import Empresa, ContaContabilEmpresa, PlanoContasImportEvent
from core.plano_contas_snapshots import importar_snapshot, selecionar_snapshot
from core.plano_contas_snapshots import SnapshotConflict, resolver_conflito
from core.models import Usuario
from core.review_items import claim_review_item
from tests.conftest import TestingSessionLocal
import pytest


def _contas(nome="Banco"):
    return [
        {"codigo": 100, "classificacao": "1.1", "nome": nome, "tipo": "A", "grau": 2}
    ]


def test_importacao_equivalente_reutiliza_snapshot_e_preserva_eventos(client):
    with TestingSessionLocal() as session:
        empresa = Empresa(
            nome_empresa="Empresa snapshot",
            api_key="snapshot-1",
            cnpj_cpf="00000000000191",
            cod_dominio=991,
        )
        session.add(empresa)
        session.flush()
        first = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas(),
            vigencia=date(2026, 1, 1),
            origem="teste-1",
        )
        second = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=[dict(_contas()[0], nome=" Banco ")],
            vigencia=date(2026, 1, 1),
            origem="teste-2",
        )
        assert first.snapshot.id == second.snapshot.id
        assert first.evento.id != second.evento.id
        assert (
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2026, 1, 1)
            ).id
            == first.snapshot.id
        )


def test_conflito_bloqueia_selecao_ate_decisao_justificada(client):
    with TestingSessionLocal() as session:
        empresa = Empresa(
            nome_empresa="Empresa conflito",
            api_key="snapshot-2",
            cnpj_cpf="00000000000192",
            cod_dominio=992,
        )
        user = Usuario(
            nome="Contador",
            login="contador.snapshot",
            email="c@snapshot.test",
            senha_hash="test",
            papel="contador",
            is_active=True,
        )
        session.add_all([empresa, user])
        session.flush()
        first = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas(),
            vigencia=date(2026, 2, 1),
            origem="primeiro",
        )
        second = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas("Despesa"),
            vigencia=date(2026, 2, 1),
            origem="segundo",
        )
        assert first.review_item_id is None
        assert second.review_item_id is not None
        with pytest.raises(SnapshotConflict):
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2026, 3, 1)
            )
        claim_review_item(
            session,
            empresa_id=empresa.id,
            item_id=second.review_item_id,
            user_id=user.id,
        )
        decision = resolver_conflito(
            session,
            empresa_id=empresa.id,
            item_id=second.review_item_id,
            snapshot_id=first.snapshot.id,
            user_id=user.id,
            reason="Plano confirmado",
        )
        assert decision.selected_snapshot_id == first.snapshot.id
        assert (
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2026, 3, 1)
            ).id
            == first.snapshot.id
        )
        third = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas("Caixa"),
            vigencia=date(2026, 2, 1),
            origem="terceiro",
        )
        assert third.review_item_id != second.review_item_id
        with pytest.raises(SnapshotConflict):
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2026, 3, 1)
            )


def test_importacao_retroativa_preserva_versoes_e_identidade_atual(client):
    with TestingSessionLocal() as session:
        empresa = Empresa(
            nome_empresa="Empresa retroativa",
            api_key="snapshot-3",
            cnpj_cpf="00000000000195",
            cod_dominio=995,
        )
        session.add(empresa)
        session.flush()
        atual = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas("Nome atual"),
            vigencia=date(2026, 8, 1),
            origem="atual",
        )
        identity = (
            session.query(ContaContabilEmpresa)
            .filter_by(empresa_id=empresa.id, codigo=100)
            .one()
        )
        old = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas("Nome anterior"),
            vigencia=date(2025, 1, 1),
            origem="historico",
        )
        inferred = importar_snapshot(
            session,
            empresa_id=empresa.id,
            contas=_contas("Nome atual"),
            vigencia=None,
            origem="sem-data",
        )
        assert inferred.snapshot.id == atual.snapshot.id
        assert inferred.evento.vigencia_inferida is True
        assert (
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2025, 6, 1)
            ).id
            == old.snapshot.id
        )
        assert (
            selecionar_snapshot(
                session, empresa_id=empresa.id, competencia=date(2026, 9, 1)
            ).id
            == atual.snapshot.id
        )
        assert identity.nome == "Nome atual"
        assert (
            session.query(PlanoContasImportEvent)
            .filter_by(empresa_id=empresa.id)
            .count()
            == 3
        )
