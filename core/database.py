from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings
"""
Módulo de configuração do banco de dados utilizando SQLAlchemy.

Este arquivo estabelece a conexão com o banco de dados, define o local do 
banco de dados e a classe base para os modelos declarativos (Base) 
da aplicação, utilizando as configurações carregadas do ambiente.
"""

def build_engine_kwargs(database_url: str) -> dict:
    if make_url(database_url).get_backend_name() == "sqlite":
        return {"connect_args": {"check_same_thread": False}}

    return {}


engine = create_engine(settings.DATABASE_URL, **build_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
