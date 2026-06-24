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
        # Como o movimento da fixture tem direcao="saida":
        assert result.conta_debito == 100
        assert result.conta_credito == mov.conta_financeira

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
