from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import DB_DEPENDENCY, verify_api_key
from core.ml_engine import ClassificadorContabil
from core.models import Empresa, Transacao

router = APIRouter()


# POST - Busca as transações pendentes de classificação
@router.post("/companies/{company_id}/classification")
def trigger_classification(
    company_id: int,
    db: Session = DB_DEPENDENCY,
    empresa: Empresa = Depends(verify_api_key),
):
    empresa = db.query(Empresa).filter(Empresa.id == company_id).first()
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
        db.query(Transacao)
        .filter(
            Transacao.empresa_id == company_id,
            Transacao.conta_contabil == None,
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
        raise HTTPException(
            status_code=500, detail=f"Erro ao classificar transações: {e}"
        )
