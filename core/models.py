from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

"""
Módulo de modelos de dados da aplicação.
Este arquivo define as entidades do banco de dados e seus relacionamentos utilizando SQLAlchemy ORM.
"""


class Empresa(Base):
    """
    Representa uma empresa cliente no sistema.
    Armazena informações de identificação, chaves de acesso e metadados.
    """

    __tablename__ = "empresas"

    # Identificador único da empresa (Chave Primária)
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Nome ou Razão Social
    nome_empresa: Mapped[str] = mapped_column(String(100), nullable=False)

    # Chave única para autenticação de requisições via API
    api_key: Mapped[str] = mapped_column(
        String(70), unique=True, index=True, nullable=False
    )

    # Cadastro de Pessoa Jurídica ou Física
    cnpj_cpf: Mapped[str] = mapped_column(
        String(15), unique=True, index=True, nullable=False
    )

    # Código identificador interno do sistema Domínio
    cod_dominio: Mapped[int] = mapped_column(Integer, nullable=False)

    # Data de criação do registro no banco de dados
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relacionamento One-to-Many: Uma empresa pode ter múltiplas transações
    # 'cascade' garante que ao deletar uma empresa, suas transações também sejam removidas
    transacoes: Mapped[list["Transacao"]] = relationship(
        "Transacao", back_populates="empresa", cascade="all, delete-orphan"
    )


class Transacao(Base):
    """
    Representa uma movimentação financeira de uma empresa.
    Contém dados da transação bancária e informações resultantes do processo de classificação contábil.
    """

    __tablename__ = "transacoes"

    # Identificador único da transação
    id: Mapped[int] = mapped_column(primary_key=True)

    # Referência (FK) para a empresa à qual esta transação pertence
    empresa_id: Mapped[int] = mapped_column(Integer, ForeignKey("empresas.id"))

    # Data da ocorrência do fato contábil
    data: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Código identificador da instituição financeira
    cod_banco: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Texto descritivo da movimentação (extrato)
    historico: Mapped[str] = mapped_column(String, nullable=False)

    # Valor da transação com precisão decimal (10 dígitos totais, 2 decimais)
    valor: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)

    # --- Atributos de Classificação Contábil ---

    # Código da conta contábil onde o lançamento será classificado (preenchido após classificação)
    conta_contabil: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Índice de confiança (0.0 a 1.0) da IA/Algoritmo na classificação (preenchido após classificação)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Indica se a transação foi marcada para conferência manual
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    # Indica se a transação já passou pelo processo de classificação
    is_classified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadados de controle temporal
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relacionamento Many-to-One: Referência para o objeto Empresa pai
    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="transacoes")
