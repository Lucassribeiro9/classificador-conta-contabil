from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import SessionLocal
from core.ml_engine import ClassificadorContabil
from core.models import models

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# POST - Busca as transações pendentes de classificação
@router.post("/companies/{empresa_id}/classification")
def trigger_classification(company_id: int, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == company_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    """Dispara a classificação das transações pendentes"""
    engine_ml = ClassificadorContabil(db)
    # Treina o modelo com o histórico da empresa
    success_train = engine_ml.train_for_company(company_id)
    if not success_train:
        raise HTTPException(
            status_code=500,
            detail="Erro ao treinar o modelo. Dados insuficientes para classificar",
        )

    # Busca ID das transações sem conta
    pendentes = (
        db.query(models.Transacao)
        .filter(
            models.Transacao.empresa_id == company_id,
            models.Transacao.conta_contabil is None,
        )
        .all()
    )
    if not pendentes:
        return {"message": "Nenhuma transação pendente encontrada"}
    ids_for_process = [t.id for t in pendentes]
    print(f"--- Classificando {len(ids_for_process)} transações...")
    # Executa o classificador
    try:
        resultados = engine_ml.classify_transactions(company_id, ids_for_process)
        return {
            "status": "sucesso",
            "empresa_id": company_id,
            "quantidade_processada": len(resultados),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao classificar transações: {e}")
