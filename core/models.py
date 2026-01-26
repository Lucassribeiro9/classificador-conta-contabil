from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, DATE, NUMERIC
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True)
    nome = Column(String)
    api_key = Column(String)
    cnpj_cpf = Column(String)
    cod_dominio = Column(Integer)
    created_at = Column(DateTime, default=datetime.now())
    