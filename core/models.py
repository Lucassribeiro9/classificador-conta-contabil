from datetime import date, datetime, timezone
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
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
    fechamentos_razao_mensais: Mapped[list["FechamentoRazaoMensal"]] = relationship(
        "FechamentoRazaoMensal",
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
    review_items: Mapped[list["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="empresa", cascade="all, delete-orphan"
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
    assigned_review_items: Mapped[list["ReviewItem"]] = relationship(
        "ReviewItem", back_populates="assignee", foreign_keys="ReviewItem.assignee_id"
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


class ReviewItem(Base):
    """Pendencia generica que requer uma decisao humana auditavel."""

    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_review', 'resolved', 'dismissed')",
            name="ck_review_items_status",
        ),
        CheckConstraint(
            "criticality IN ('low', 'medium', 'high', 'critical')",
            name="ck_review_items_criticality",
        ),
        UniqueConstraint(
            "empresa_id",
            "source_type",
            "grouping_key",
            name="uq_review_items_company_source_group",
        ),
        Index(
            "ix_review_items_company_status_criticality_created",
            "empresa_id",
            "status",
            "criticality",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    grouping_key: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="review_items")
    assignee: Mapped[Optional["Usuario"]] = relationship(
        "Usuario",
        back_populates="assigned_review_items",
        foreign_keys=[assignee_id],
    )
    evidences: Mapped[list["ReviewEvidence"]] = relationship(
        "ReviewEvidence", back_populates="review_item", cascade="all, delete-orphan"
    )
    events: Mapped[list["ReviewItemEvent"]] = relationship(
        "ReviewItemEvent", back_populates="review_item", cascade="all, delete-orphan"
    )


class ReviewEvidence(Base):
    """Referencia segura e rastreavel a evidencia de uma pendencia."""

    __tablename__ = "review_item_evidences"
    __table_args__ = (
        UniqueConstraint(
            "review_item_id",
            "source_type",
            "source_id",
            name="uq_review_item_evidence_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(
        ForeignKey("review_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    safe_metadata: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False
    )

    review_item: Mapped["ReviewItem"] = relationship(
        "ReviewItem", back_populates="evidences"
    )


class ReviewItemEvent(Base):
    """Historico imutavel de transicoes e justificativas da pendencia."""

    __tablename__ = "review_item_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[int] = mapped_column(
        ForeignKey("review_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, server_default=func.now(), nullable=False
    )

    review_item: Mapped["ReviewItem"] = relationship(
        "ReviewItem", back_populates="events"
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
        ForeignKeyConstraint(
            ["conta_contabil_empresa_id", "empresa_id"],
            ["contas_contabeis_empresas.id", "contas_contabeis_empresas.empresa_id"],
            name="fk_empresa_contas_contabeis_identidade_empresa",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    conta_codigo: Mapped[int] = mapped_column(
        Integer, ForeignKey("contas_contabeis.codigo"), nullable=False
    )
    conta_contabil_empresa_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
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
    identidade_empresa: Mapped[Optional["ContaContabilEmpresa"]] = relationship(
        "ContaContabilEmpresa",
        viewonly=True,
    )


class ContaContabilEmpresa(Base):
    """Identidade contabil estavel e atributos atuais no contexto da empresa."""

    __tablename__ = "contas_contabeis_empresas"
    __table_args__ = (
        CheckConstraint("tipo IN ('A', 'S')", name="ck_contas_contabeis_empresas_tipo"),
        UniqueConstraint(
            "id",
            "empresa_id",
            name="uq_contas_contabeis_empresas_id_empresa",
        ),
        Index(
            "uq_contas_contabeis_empresas_empresa_codigo",
            "empresa_id",
            "codigo",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    codigo: Mapped[int] = mapped_column(Integer, nullable=False)
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
        """Indica se a identidade da empresa pode receber lançamentos."""
        return self.is_active and self.tipo == "A"


class PlanoContasSnapshot(Base):
    """Conteúdo imutável de uma versão do plano de uma empresa."""

    __tablename__ = "plano_contas_snapshots"
    __table_args__ = (
        UniqueConstraint("empresa_id", "content_hash", name="uq_plano_snapshot_content"),
        UniqueConstraint("id", "empresa_id", name="uq_plano_snapshot_id_company"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class PlanoContasImportEvent(Base):
    """Cada tentativa válida preserva sua origem e vigência, mesmo após deduplicação."""

    __tablename__ = "plano_contas_import_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_import_snapshot_company",
        ),
        Index("ix_plano_import_company_date", "empresa_id", "vigencia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    vigencia: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_inferida: Mapped[bool] = mapped_column(Boolean, nullable=False)
    origem: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class PlanoContasSnapshotEntry(Base):
    """Atributos da conta nesta versão, ligados à identidade estável."""

    __tablename__ = "plano_contas_snapshot_entries"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "codigo", name="uq_plano_snapshot_entry_code"),
        ForeignKeyConstraint(
            ["snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_snapshot_entry_snapshot_company",
        ),
        ForeignKeyConstraint(
            ["conta_contabil_empresa_id", "empresa_id"],
            ["contas_contabeis_empresas.id", "contas_contabeis_empresas.empresa_id"],
            name="fk_plano_snapshot_entry_identity_company",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    conta_contabil_empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[int] = mapped_column(Integer, nullable=False)
    classificacao: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(1), nullable=False)
    grau: Mapped[int] = mapped_column(Integer, nullable=False)


class PlanoContasConflictDecision(Base):
    """Seleção humana auditável para uma vigência com múltiplos snapshots."""

    __tablename__ = "plano_contas_conflict_decisions"
    __table_args__ = (
        UniqueConstraint("empresa_id", "vigencia", "candidate_hash", name="uq_plano_conflict_decision_candidates"),
        ForeignKeyConstraint(
            ["selected_snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_decision_snapshot_company",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    vigencia: Mapped[date] = mapped_column(Date, nullable=False)
    candidate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    review_item_id: Mapped[int] = mapped_column(ForeignKey("review_items.id"), nullable=False)
    selected_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class BackfillContasContabeisExecucao(Base):
    """Auditable lifecycle for a legacy-to-company-account backfill run."""

    __tablename__ = "backfill_contas_contabeis_execucoes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'partial', 'rolled_back', 'rollback_partial')",
            name="ck_backfill_contas_contabeis_execucoes_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class BackfillContasContabeisItem(Base):
    """Sanitized per-link outcome and ownership proof for a backfill run."""

    __tablename__ = "backfill_contas_contabeis_itens"
    __table_args__ = (
        CheckConstraint(
            "resultado IN ('created', 'already_present', 'conflict', 'ineligible', 'failed')",
            name="ck_backfill_contas_contabeis_itens_resultado",
        ),
        CheckConstraint(
            "rollback_status IS NULL OR rollback_status IN ('rolled_back', 'blocked')",
            name="ck_backfill_contas_contabeis_itens_rollback_status",
        ),
        Index(
            "uq_backfill_contas_contabeis_itens_execucao_vinculo",
            "execucao_id",
            "vinculo_legado_id",
            unique=True,
        ),
        Index(
            "ix_backfill_contas_contabeis_itens_identidade",
            "identidade_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execucao_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("backfill_contas_contabeis_execucoes.id"), nullable=False
    )
    vinculo_legado_id: Mapped[int] = mapped_column(Integer, nullable=False)
    empresa_id: Mapped[int] = mapped_column(Integer, nullable=False)
    conta_codigo: Mapped[int] = mapped_column(Integer, nullable=False)
    identidade_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resultado: Mapped[str] = mapped_column(String(24), nullable=False)
    source_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    rollback_status: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )


class LoteImportacaoRazao(Base):
    """
    Representa um lote de importacao do livro-razao de uma empresa.
    """

    __tablename__ = "lotes_importacao_razao"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'processing', 'completed', 'completed_with_warnings', 'failed')",
            name="ck_lotes_importacao_razao_status",
        ),
        CheckConstraint(
            "total_linhas IS NULL OR total_linhas >= 0",
            name="ck_lotes_importacao_razao_total_linhas",
        ),
        CheckConstraint(
            "linhas_processadas >= 0 AND total_importadas >= 0 "
            "AND total_invalidas >= 0 AND warnings_total >= 0",
            name="ck_lotes_importacao_razao_contadores_nao_negativos",
        ),
        CheckConstraint(
            "total_linhas IS NULL OR linhas_processadas <= total_linhas",
            name="ck_lotes_importacao_razao_processadas_ate_total",
        ),
        CheckConstraint(
            "(status IN ('queued', 'processing') AND "
            "total_importadas + total_invalidas <= linhas_processadas) OR "
            "(status IN ('completed', 'completed_with_warnings', 'failed') AND "
            "((total_linhas IS NULL AND total_importadas = 0 AND total_invalidas = 0) "
            "OR (total_linhas IS NOT NULL "
            "AND total_importadas + total_invalidas <= total_linhas)))",
            name="ck_lotes_importacao_razao_resultados_ate_processadas",
        ),
        CheckConstraint(
            "(usuario_id IS NOT NULL AND identidade_servico_id IS NULL) OR "
            "(usuario_id IS NULL AND identidade_servico_id IS NOT NULL)",
            name="ck_lotes_importacao_razao_solicitante",
        ),
        UniqueConstraint(
            "empresa_id",
            "file_hash",
            name="uq_lotes_importacao_razao_empresa_file_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("empresas.id"), nullable=False
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    identidade_servico_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("identidades_servico.id"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default="queued", nullable=False
    )
    total_linhas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    linhas_processadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_importadas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_invalidas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings_metadata: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"totals_by_code": {}},
        server_default='{"totals_by_code": {}}',
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_token: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    lease_owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_request_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    identidade_servico: Mapped[Optional["IdentidadeServico"]] = relationship(
        "IdentidadeServico"
    )
    lancamentos: Mapped[list["LancamentoRazaoNormalizado"]] = relationship(
        "LancamentoRazaoNormalizado",
        back_populates="lote",
        cascade="all, delete-orphan",
    )
    fechamentos_mensais: Mapped[list["FechamentoRazaoMensal"]] = relationship(
        "FechamentoRazaoMensal",
        back_populates="lote",
        cascade="all, delete-orphan",
    )
    tentativas: Mapped[list["TentativaImportacaoRazao"]] = relationship(
        "TentativaImportacaoRazao",
        back_populates="lote",
        cascade="all, delete-orphan",
        order_by="TentativaImportacaoRazao.numero",
    )
    warnings_normalizados: Mapped[list["WarningImportacaoRazao"]] = relationship(
        "WarningImportacaoRazao",
        back_populates="lote",
        cascade="all, delete-orphan",
    )


class TentativaImportacaoRazao(Base):
    """Registra uma tentativa de processamento de um lote do Razao."""

    __tablename__ = "tentativas_importacao_razao"
    __table_args__ = (
        CheckConstraint(
            "resultado IS NULL OR resultado IN "
            "('completed', 'completed_with_warnings', 'failed', 'interrupted')",
            name="ck_tentativas_importacao_razao_resultado",
        ),
        UniqueConstraint(
            "lote_id",
            "numero",
            name="uq_tentativas_importacao_razao_lote_numero",
        ),
        Index("ix_tentativas_importacao_razao_lote_id", "lote_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lotes_importacao_razao.id", ondelete="CASCADE"),
        nullable=False,
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resultado: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_request_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    lote: Mapped["LoteImportacaoRazao"] = relationship(
        "LoteImportacaoRazao", back_populates="tentativas"
    )


class WarningImportacaoRazao(Base):
    """Persiste um aviso seguro e estruturado produzido na importacao do Razao."""

    __tablename__ = "warnings_importacao_razao"
    __table_args__ = (
        Index("ix_warnings_importacao_razao_lote_id_id", "lote_id", "id"),
        Index(
            "ix_warnings_importacao_razao_lote_codigo_linha",
            "lote_id",
            "codigo",
            "linha",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lotes_importacao_razao.id", ondelete="CASCADE"),
        nullable=False,
    )
    linha: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    mensagem: Mapped[str] = mapped_column(String(500), nullable=False)
    detalhes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lote: Mapped["LoteImportacaoRazao"] = relationship(
        "LoteImportacaoRazao", back_populates="warnings_normalizados"
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
        CheckConstraint(
            "saldo_anterior_natureza IS NULL OR saldo_anterior_natureza IN ('D', 'C')",
            name="ck_lancamentos_razao_normalizados_saldo_anterior_natureza",
        ),
        CheckConstraint(
            "saldo_natureza IS NULL OR saldo_natureza IN ('D', 'C')",
            name="ck_lancamentos_razao_normalizados_saldo_natureza",
        ),
        CheckConstraint(
            "saldo_exercicio_natureza IS NULL OR saldo_exercicio_natureza IN ('D', 'C')",
            name="ck_lancamentos_razao_normalizados_saldo_exercicio_natureza",
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
    valor: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2), nullable=False
    )
    saldo_anterior_original: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    saldo_anterior_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    saldo_anterior_natureza: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )
    saldo_original: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    saldo_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    saldo_natureza: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    saldo_exercicio_original: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    saldo_exercicio_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    saldo_exercicio_natureza: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )
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


class FechamentoRazaoMensal(Base):
    """Representa o fechamento mensal derivado do Razao por empresa e conta."""

    __tablename__ = "fechamentos_razao_mensais"
    __table_args__ = (
        CheckConstraint(
            "mes >= 1 AND mes <= 12",
            name="ck_fechamentos_razao_mensais_mes",
        ),
        CheckConstraint(
            "saldo_observado_natureza IS NULL OR saldo_observado_natureza IN ('D', 'C')",
            name="ck_fechamentos_razao_mensais_saldo_observado_natureza",
        ),
        UniqueConstraint(
            "empresa_id",
            "conta_codigo",
            "ano",
            "mes",
            "lote_id",
            name="uq_fechamentos_razao_mensais_empresa_conta_mes_lote",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lotes_importacao_razao.id", ondelete="CASCADE"),
        nullable=False,
    )
    empresa_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
    )
    conta_codigo: Mapped[int] = mapped_column(Integer, nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_observado_original: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    saldo_observado_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    saldo_observado_natureza: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )
    saldo_observado_fonte: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    saldo_calculado_decimal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=14, scale=2), nullable=True
    )
    warnings_saldo: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    lote: Mapped["LoteImportacaoRazao"] = relationship(
        "LoteImportacaoRazao", back_populates="fechamentos_mensais"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="fechamentos_razao_mensais"
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
