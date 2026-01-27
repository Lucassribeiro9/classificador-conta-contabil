from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Date, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"
    id = Column(Integer, primary_key=True, index=True)
    nome_empresa = Column(String, unique=True, index=True, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    cnpj_cpf = Column(String, unique=True, index=True, nullable=False)
    cod_dominio = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    transacoes = relationship("Transacao", back_populates="empresa", cascade="all, delete-orphan")

class Transacao(Base):
    __tablename__ = "transacoes"
    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"))
    data = Column(Date, nullable=False)
    cod_banco = Column(Integer, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Numeric(precision=10, scale=2), nullable=False)
    
    # Classificação
    conta_contabil = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    needs_review = Column(Boolean, default=False)
    is_classified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    empresa = relationship("Empresa", back_populates="transacoes")