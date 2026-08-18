import pytest
from datetime import date
from core.models import MovimentoOperacionalImportado, ContaContabil, EmpresaContaContabil
from core.movimentos_operacionais_review import review_movimento_operacional, MovimentoReviewError
from tests.conftest import TestingSessionLocal
from tests.test_movimentos_operacionais_api import _seed_operational_lote_with_movements, _conta, _vinculo

def test_approve_movimento_sets_status_and_final_conta(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="operacao")
    
    with TestingSessionLocal() as session:
        conta = ContaContabil(codigo=100, classificacao="1.0.0", nome="Conta", tipo="A", grau=3)
        session.add(conta)
        session.commit()

        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov_id = mov.id

        result = review_movimento_operacional(
            db=session,
            movimento_id=mov_id,
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            action="approve",
            conta_final=100
        )
        
        assert result.status == "aprovado"
        assert result.contrapartida_final == 100
        assert result.elegivel_treino is True
        # Como o movimento da fixture tem direcao="credito":
        assert result.conta_debito == 100
        assert result.conta_credito == mov.conta_financeira


def test_approve_debit_direction_debits_financial_account(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="operacao")

    with TestingSessionLocal() as session:
        conta = ContaContabil(codigo=100, classificacao="1.0.0", nome="Conta", tipo="A", grau=3)
        session.add(conta)
        session.commit()

        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov.direcao = "debito"
        mov_id = mov.id

        result = review_movimento_operacional(
            db=session,
            movimento_id=mov_id,
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            action="approve",
            conta_final=100
        )

        assert result.conta_debito == mov.conta_financeira
        assert result.conta_credito == 100


def test_reject_movimento(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(permissao="operacao")
    
    with TestingSessionLocal() as session:
        mov = session.query(MovimentoOperacionalImportado).filter_by(lote_id=lote_id).first()
        mov_id = mov.id

        result = review_movimento_operacional(
            db=session,
            movimento_id=mov_id,
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            action="reject"
        )
        
        assert result.status == "rejeitado"
        assert result.contrapartida_final is None
        assert result.elegivel_treino is False
        assert result.conta_debito is None
        assert result.conta_credito is None


def test_review_rejects_finalized_status_without_changing_movement(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        conta = ContaContabil(
            codigo=100,
            classificacao="1.0.0",
            nome="Conta",
            tipo="A",
            grau=3,
        )
        session.add(conta)
        session.commit()

        mov = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .first()
        )
        mov.status = "aprovado"
        mov.contrapartida_final = 20001
        mov.conta_debito = 20001
        mov.conta_credito = mov.conta_financeira
        mov.elegivel_treino = True
        session.flush()

        with pytest.raises(MovimentoReviewError, match="Status não permite revisão"):
            review_movimento_operacional(
                db=session,
                movimento_id=mov.id,
                empresa_id=empresa_id,
                usuario_id=usuario.id,
                action="correct",
                conta_final=100,
            )

        assert mov.status == "aprovado"
        assert mov.contrapartida_final == 20001
        assert mov.conta_debito == 20001
        assert mov.conta_credito == 10046
        assert mov.elegivel_treino is True


def test_reject_clears_existing_final_accounts(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        mov = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .first()
        )
        mov.status = "revisao"
        mov.contrapartida_final = 20001
        mov.conta_debito = 20001
        mov.conta_credito = mov.conta_financeira
        mov.elegivel_treino = True
        session.flush()

        result = review_movimento_operacional(
            db=session,
            movimento_id=mov.id,
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            action="reject",
        )

        assert result.status == "rejeitado"
        assert result.contrapartida_final is None
        assert result.conta_debito is None
        assert result.conta_credito is None
        assert result.elegivel_treino is False


def test_approve_preserves_input_suggestion_and_confidence(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        conta = ContaContabil(
            codigo=100,
            classificacao="1.0.0",
            nome="Conta",
            tipo="A",
            grau=3,
        )
        session.add(conta)
        session.commit()

        mov = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .first()
        )
        mov.contrapartida_informada = 20001
        mov.contrapartida_sugerida = 30001
        mov.confidence_sugerida = 0.87
        session.flush()

        result = review_movimento_operacional(
            db=session,
            movimento_id=mov.id,
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            action="approve",
            conta_final=100,
        )

        assert result.contrapartida_final == 100
        assert result.contrapartida_informada == 20001
        assert result.contrapartida_sugerida == 30001
        assert result.confidence_sugerida == 0.87


def test_correct_rejects_inactive_or_synthetic_account(setup_db):
    usuario, empresa_id, lote_id = _seed_operational_lote_with_movements(
        permissao="operacao"
    )

    with TestingSessionLocal() as session:
        inactive = ContaContabil(
            codigo=101,
            classificacao="1.0.1",
            nome="Inativa",
            tipo="A",
            grau=3,
            is_active=False,
        )
        synthetic = ContaContabil(
            codigo=102,
            classificacao="1.0",
            nome="Sintetica",
            tipo="S",
            grau=2,
            is_active=True,
        )
        session.add_all([inactive, synthetic])
        session.commit()

        mov = (
            session.query(MovimentoOperacionalImportado)
            .filter_by(lote_id=lote_id)
            .first()
        )
        for conta_final in (101, 102):
            with pytest.raises(
                MovimentoReviewError,
                match="Conta final inválida ou inativa",
            ):
                review_movimento_operacional(
                    db=session,
                    movimento_id=mov.id,
                    empresa_id=empresa_id,
                    usuario_id=usuario.id,
                    action="correct",
                    conta_final=conta_final,
                )

        assert mov.status == "pre_classificado"
        assert mov.contrapartida_final is None
        assert mov.conta_debito is None
        assert mov.conta_credito is None
