from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    func,
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
        String(14), unique=True, index=True, nullable=False
    )

    # Código identificador interno do sistema Domínio
    cod_dominio: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # Status da empresa (Ativa/Inativa)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Data de criação do registro no banco de dados
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relacionamento One-to-Many: Uma empresa pode ter múltiplas transações
    # 'cascade' garante que ao deletar uma empresa, suas transações também sejam removidas
    transacoes: Mapped[list["Transacao"]] = relationship(
        "Transacao", back_populates="empresa", cascade="all, delete-orphan"
    )

    permissoes_usuarios: Mapped[list["UsuarioEmpresaPermissao"]] = relationship(
        "UsuarioEmpresaPermissao",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    lotes_importacao_razao: Mapped[list["LoteImportacaoRazao"]] = relationship(
        "LoteImportacaoRazao",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    lotes_importacao_movimentos_operacionais: Mapped[
        list["LoteImportacaoMovimentoOperacional"]
    ] = relationship(
        "LoteImportacaoMovimentoOperacional",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    lancamentos_razao: Mapped[list["LancamentoRazaoNormalizado"]] = relationship(
        "LancamentoRazaoNormalizado",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    movimentos_operacionais: Mapped[list["MovimentoOperacionalImportado"]] = (
        relationship(
            "MovimentoOperacionalImportado",
            back_populates="empresa",
            cascade="all, delete-orphan",
        )
    )
    contas_contabeis_usadas: Mapped[list["EmpresaContaContabil"]] = relationship(
        "EmpresaContaContabil",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    feedbacks_classificacao: Mapped[list["FeedbackClassificacao"]] = relationship(
        "FeedbackClassificacao",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="empresa",
    )
    identidades_servico: Mapped[list["IdentidadeServicoEmpresa"]] = relationship(
        "IdentidadeServicoEmpresa",
        back_populates="empresa",
        cascade="all, delete-orphan",
    )


class Usuario(Base):
    """
    Representa um usuario interno do escritorio.
    """

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "papel IN ('admin', 'contador', 'operador')",
            name="ck_usuarios_papel",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    permissoes_empresas: Mapped[list["UsuarioEmpresaPermissao"]] = relationship(
        "UsuarioEmpresaPermissao",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    lotes_importacao_razao: Mapped[list["LoteImportacaoRazao"]] = relationship(
        "LoteImportacaoRazao",
        back_populates="usuario",
    )
    lotes_importacao_movimentos_operacionais: Mapped[
        list["LoteImportacaoMovimentoOperacional"]
    ] = relationship(
        "LoteImportacaoMovimentoOperacional",
        back_populates="usuario",
    )
    feedbacks_classificacao: Mapped[list["FeedbackClassificacao"]] = relationship(
        "FeedbackClassificacao",
        back_populates="usuario",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent",
        back_populates="usuario",
    )


class UsuarioEmpresaPermissao(Base):
    """
    Vincula um usuario interno a uma empresa com uma permissao operacional.
    """

    __tablename__ = "usuario_empresa_permissoes"
    __table_args__ = (
        CheckConstraint(
            "permissao IN ('leitura', 'operacao', 'admin_empresa')",
            name="ck_usuario_empresa_permissoes_permissao",
        ),
        Index(
            "uq_usuario_empresa_permissoes_usuario_empresa",
            "usuario_id",
            "empresa_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    permissao: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="permissoes_empresas"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="permissoes_usuarios"
    )


class IdentidadeServico(Base):
    """Representa uma identidade propria para integracoes automatizadas."""

    __tablename__ = "identidades_servico"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ativa', 'inativa', 'revogada')",
            name="ck_identidades_servico_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    credential_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    credential_fingerprint: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="ativa", nullable=False)
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    revoked_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    empresas: Mapped[list["IdentidadeServicoEmpresa"]] = relationship(
        "IdentidadeServicoEmpresa",
        back_populates="identidade_servico",
        cascade="all, delete-orphan",
    )
    escopos: Mapped[list["IdentidadeServicoEscopo"]] = relationship(
        "IdentidadeServicoEscopo",
        back_populates="identidade_servico",
        cascade="all, delete-orphan",
    )


class IdentidadeServicoEmpresa(Base):
    """Vincula uma identidade de servico a uma empresa autorizada."""

    __tablename__ = "identidade_servico_empresas"
    __table_args__ = (
        Index(
            "uq_identidade_servico_empresas_identidade_empresa",
            "identidade_servico_id",
            "empresa_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    identidade_servico_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("identidades_servico.id", ondelete="CASCADE"), nullable=False
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    identidade_servico: Mapped["IdentidadeServico"] = relationship(
        "IdentidadeServico", back_populates="empresas"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="identidades_servico"
    )


class IdentidadeServicoEscopo(Base):
    """Escopo concedido a uma identidade de servico."""

    __tablename__ = "identidade_servico_escopos"
    __table_args__ = (
        CheckConstraint(
            "escopo IN ('empresas:read', 'ml:classificar', "
            "'movimentos:download', 'movimentos:feedback')",
            name="ck_identidade_servico_escopos_escopo",
        ),
        Index(
            "uq_identidade_servico_escopos_identidade_escopo",
            "identidade_servico_id",
            "escopo",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    identidade_servico_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("identidades_servico.id", ondelete="CASCADE"), nullable=False
    )
    escopo: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    identidade_servico: Mapped["IdentidadeServico"] = relationship(
        "IdentidadeServico", back_populates="escopos"
    )


class AuditEvent(Base):
    """
    Evento central de auditoria para acoes sensiveis do sistema.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    empresa_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=True
    )
    resource_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    usuario: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", back_populates="audit_events"
    )
    empresa: Mapped[Optional["Empresa"]] = relationship(
        "Empresa", back_populates="audit_events"
    )


class ContaContabil(Base):
    """
    Representa uma conta do catalogo unico do plano de contas do escritorio.
    """

    __tablename__ = "contas_contabeis"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('A', 'S')",
            name="ck_contas_contabeis_tipo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    classificacao: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    grau: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_financial_origin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    @property
    def is_classificavel(self) -> bool:
        """Indica se a conta pode ser usada como alvo de classificacao."""
        return self.is_active and self.tipo == "A"


class EmpresaContaContabil(Base):
    """
    Vincula uma empresa as contas contabeis encontradas em importacoes validas.
    """

    __tablename__ = "empresa_contas_contabeis"
    __table_args__ = (
        Index(
            "uq_empresa_contas_contabeis_empresa_conta",
            "empresa_id",
            "conta_codigo",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    conta_codigo: Mapped[int] = mapped_column(
        Integer, ForeignKey("contas_contabeis.codigo"), nullable=False
    )
    quantidade_lancamentos: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    ultima_utilizacao: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="contas_contabeis_usadas"
    )
    conta: Mapped["ContaContabil"] = relationship("ContaContabil")


class LoteImportacaoRazao(Base):
    """
    Representa um lote de importacao do livro-razao de uma empresa.
    """

    __tablename__ = "lotes_importacao_razao"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'completed_with_warnings', 'failed')",
            name="ck_lotes_importacao_razao_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_linhas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_importadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_invalidas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="lotes_importacao_razao"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="lotes_importacao_razao"
    )
    lancamentos: Mapped[list["LancamentoRazaoNormalizado"]] = relationship(
        "LancamentoRazaoNormalizado",
        back_populates="lote",
        cascade="all, delete-orphan",
    )


class LancamentoRazaoNormalizado(Base):
    """
    Representa uma linha valida do razao normalizada em debito/credito.
    """

    __tablename__ = "lancamentos_razao_normalizados"
    __table_args__ = (
        CheckConstraint(
            "direcao IN ('debito', 'credito')",
            name="ck_lancamentos_razao_normalizados_direcao",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lotes_importacao_razao.id"), nullable=False
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    numero_lancamento: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[datetime] = mapped_column(Date, nullable=False)
    conta_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    conta_contrapartida: Mapped[int] = mapped_column(Integer, nullable=False)
    conta_debito: Mapped[int] = mapped_column(Integer, nullable=False)
    conta_credito: Mapped[int] = mapped_column(Integer, nullable=False)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)
    historico: Mapped[str] = mapped_column(String, nullable=False)
    historico_normalizado: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(precision=12, scale=2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    lote: Mapped["LoteImportacaoRazao"] = relationship(
        "LoteImportacaoRazao", back_populates="lancamentos"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="lancamentos_razao"
    )
    feedbacks_classificacao: Mapped[list["FeedbackClassificacao"]] = relationship(
        "FeedbackClassificacao",
        back_populates="lancamento",
        cascade="all, delete-orphan",
    )


class FeedbackClassificacao(Base):
    """
    Registra correcao humana para classificacao de contrapartida do razao.
    """

    __tablename__ = "feedback_classificacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    lancamento_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lancamentos_razao_normalizados.id"), nullable=False
    )
    conta_sugerida: Mapped[int] = mapped_column(Integer, nullable=False)
    conta_final: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="feedbacks_classificacao"
    )
    lancamento: Mapped["LancamentoRazaoNormalizado"] = relationship(
        "LancamentoRazaoNormalizado", back_populates="feedbacks_classificacao"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="feedbacks_classificacao"
    )


class LoteImportacaoMovimentoOperacional(Base):
    """
    Representa um lote de importacao de movimentos operacionais.
    """

    __tablename__ = "lotes_importacao_movimentos_operacionais"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'completed_with_warnings', 'failed')",
            name="ck_lotes_importacao_movimentos_operacionais_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    total_linhas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_importadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_invalidas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False)
    cnpj_cpf_arquivo: Mapped[str] = mapped_column(String(14), nullable=False)
    codigo_dominio_arquivo: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    layout_version: Mapped[str] = mapped_column(
        String(80), default="operacional_valor_legado_v1", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="lotes_importacao_movimentos_operacionais"
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="lotes_importacao_movimentos_operacionais"
    )
    movimentos: Mapped[list["MovimentoOperacionalImportado"]] = relationship(
        "MovimentoOperacionalImportado",
        back_populates="lote",
        cascade="all, delete-orphan",
    )


class MovimentoOperacionalImportado(Base):
    """
    Representa uma linha operacional importada para classificacao e revisao.
    """

    __tablename__ = "movimentos_operacionais_importados"
    __table_args__ = (
        CheckConstraint(
            "direcao IN ('debito', 'credito')",
            name="ck_movimentos_operacionais_importados_direcao",
        ),
        CheckConstraint(
            "status IN ("
            "'pendente', 'pre_classificado', 'sugerido', 'revisao', "
            "'aprovado', 'corrigido', 'rejeitado', 'convertido'"
            ")",
            name="ck_movimentos_operacionais_importados_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lotes_importacao_movimentos_operacionais.id"),
        nullable=False,
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    conta_financeira: Mapped[int] = mapped_column(Integer, nullable=False)
    historico: Mapped[str] = mapped_column(String, nullable=False)
    historico_normalizado: Mapped[str] = mapped_column(String, nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    valor_absoluto: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    saldo_observado_original: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    saldo_observado_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    saldo_calculado_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    warnings_saldo: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)
    tipo_movimento: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    documento: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linha_original: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contrapartida_informada: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    contrapartida_sugerida: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    contrapartida_final: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_sugerida: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    elegivel_treino: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    mensagens_validacao: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    conta_debito: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    conta_credito: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    lote: Mapped["LoteImportacaoMovimentoOperacional"] = relationship(
        "LoteImportacaoMovimentoOperacional", back_populates="movimentos"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="movimentos_operacionais"
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

# Índice de unicidade para evitar duplicação de transações idênticas
Index(
    "uq_transacao_dedup",
    Transacao.empresa_id,
    Transacao.data,
    Transacao.historico,
    Transacao.valor,
    func.coalesce(Transacao.conta_contabil, -1),
    func.coalesce(Transacao.cod_banco, -1),
    unique=True,
)

# Índices para otimização de consultas frequentes
Index("ix_transacoes_empresa_id_id", Transacao.empresa_id, Transacao.id)

Index(
    "ix_transacoes_empresa_data_banco_conta",
    Transacao.empresa_id,
    Transacao.data,
    Transacao.cod_banco,
    Transacao.conta_contabil,
    Transacao.id,
)
