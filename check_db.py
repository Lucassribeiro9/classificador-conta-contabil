from core.database import engine, Base
from core.models import Empresa, Transacao

"""
Script para verificar se o banco de dados foi criado corretamente.
"""
print("Creating database...")
Base.metadata.create_all(bind=engine)
print("Database created successfully")