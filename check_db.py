from core.database import engine, Base
from core.models import Empresa, Transacao

print("Creating database...")
Base.metadata.create_all(bind=engine)
print("Database created successfully")