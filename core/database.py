from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings
"""
Módulo de configuração do banco de dados utilizando SQLAlchemy.

Este arquivo estabelece a conexão com o banco de dados, define o local do 
banco de dados e a classe base para os modelos declarativos (Base) 
da aplicação, utilizando as configurações carregadas do ambiente.
"""

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
