from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.routes import auth, classification, companies, feedback, plano_contas, razao, transactions, users
from core.audit import begin_audit_request_context, end_audit_request_context


app = FastAPI(title="Classificador contábil")


@app.middleware("http")
async def audit_context_middleware(request, call_next):
    begin_audit_request_context()
    try:
        return await call_next(request)
    finally:
        end_audit_request_context()


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
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(companies.router, prefix="/api/v1", tags=["Empresas"])
app.include_router(transactions.router, prefix="/api/v1", tags=["Transações"])
app.include_router(classification.router, prefix="/api/v1", tags=["Classificação"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])
app.include_router(users.router, prefix="/api/v1", tags=["Usuários"])
app.include_router(
    plano_contas.admin_router,
    prefix="/api/v1",
    tags=["Plano de Contas"],
)
app.include_router(
    plano_contas.catalog_router,
    prefix="/api/v1",
    tags=["Plano de Contas"],
)
app.include_router(razao.router, prefix="/api/v1", tags=["Razão"])


@app.get("/")
def read_root():
    return {"message": "API de Classificação de Contas Contábeis"}
