from core.database import engine, Base
from core.models import Empresa, Transacao
import os

# 1. Caminho do banco
DB_FILE = "classificador.db"

# 2. Se o banco já existe, removemos para recriar do zero (limpeza de dev)
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Banco antigo '{DB_FILE}' removido.")

# 3. Cria as tabelas baseadas nos novos modelos
print("Criando tabelas conforme o novo UML...")
Base.metadata.create_all(bind=engine)
print("Sucesso! Tabelas 'empresas' e 'transacoes' criadas.")