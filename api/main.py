from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.routes import classification, companies, feedback, transactions

app = FastAPI(title="Classificador contábil")


# Checando se está tudo certo
@app.get("/health", tags=["Sistema"])
def health_check(db: Session = Depends(get_db)):
    # Verifica se API e banco estão operacionais
    try:
        # Executa query de checagem
        db.execute(text("SELECT 1"))
        db_status = "online"

    except Exception as e:
        db_status = f"offline. Erro: {str(e)}"
    return {
        "status": "online" if db_status == "online" else "offline",
        "database": db_status,
        "api_version": "v1",
        "env": "desenvolvimento",
    }


# Rotas
app.include_router(companies.router, prefix="/api/v1", tags=["Empresas"])
app.include_router(transactions.router, prefix="/api/v1", tags=["Transações"])
app.include_router(classification.router, prefix="/api/v1", tags=["Classificação"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])


@app.get("/")
def read_root():
    return {"message": "API de Classificação de Contas Contábeis"}
