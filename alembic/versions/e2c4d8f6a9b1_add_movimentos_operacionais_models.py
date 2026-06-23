"""add movimentos operacionais models

Revision ID: e2c4d8f6a9b1
Revises: d7a3c5e9f102
Create Date: 2026-06-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2c4d8f6a9b1"
down_revision: Union[str, Sequence[str], None] = "d7a3c5e9f102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lotes_importacao_movimentos_operacionais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("total_linhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_importadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_invalidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "warnings_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("cnpj_cpf_arquivo", sa.String(length=14), nullable=False),
        sa.Column("codigo_dominio_arquivo", sa.String(length=30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'completed_with_warnings', 'failed')",
            name="ck_lotes_importacao_movimentos_operacionais_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lotes_importacao_movimentos_operacionais_empresa_id"),
        "lotes_importacao_movimentos_operacionais",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        "ix_lotes_importacao_movimentos_operacionais_empresa_file_hash",
        "lotes_importacao_movimentos_operacionais",
        ["empresa_id", "file_hash"],
        unique=False,
    )

    op.create_table(
        "movimentos_operacionais_importados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("conta_financeira", sa.Integer(), nullable=False),
        sa.Column("historico", sa.String(), nullable=False),
        sa.Column("historico_normalizado", sa.String(), nullable=False),
        sa.Column(
            "valor_original",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "valor_absoluto",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column("direcao", sa.String(length=10), nullable=False),
        sa.Column("tipo_movimento", sa.String(length=40), nullable=True),
        sa.Column("documento", sa.String(length=120), nullable=True),
        sa.Column("observacao", sa.String(), nullable=True),
        sa.Column("contrapartida_informada", sa.Integer(), nullable=True),
        sa.Column("contrapartida_sugerida", sa.Integer(), nullable=True),
        sa.Column("contrapartida_final", sa.Integer(), nullable=True),
        sa.Column("confidence_sugerida", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "elegivel_treino",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "mensagens_validacao",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("conta_debito", sa.Integer(), nullable=True),
        sa.Column("conta_credito", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "direcao IN ('entrada', 'saida')",
            name="ck_movimentos_operacionais_importados_direcao",
        ),
        sa.CheckConstraint(
            "status IN ("
            "'pendente', 'pre_classificado', 'sugerido', 'revisao', "
            "'aprovado', 'corrigido', 'rejeitado', 'convertido'"
            ")",
            name="ck_movimentos_operacionais_importados_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["lote_id"],
            ["lotes_importacao_movimentos_operacionais.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_movimentos_operacionais_importados_empresa_id"),
        "movimentos_operacionais_importados",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_movimentos_operacionais_importados_lote_id"),
        "movimentos_operacionais_importados",
        ["lote_id"],
        unique=False,
    )
    op.create_index(
        "ix_movimentos_operacionais_importados_empresa_status",
        "movimentos_operacionais_importados",
        ["empresa_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_movimentos_operacionais_importados_empresa_status",
        table_name="movimentos_operacionais_importados",
    )
    op.drop_index(
        op.f("ix_movimentos_operacionais_importados_lote_id"),
        table_name="movimentos_operacionais_importados",
    )
    op.drop_index(
        op.f("ix_movimentos_operacionais_importados_empresa_id"),
        table_name="movimentos_operacionais_importados",
    )
    op.drop_table("movimentos_operacionais_importados")
    op.drop_index(
        "ix_lotes_importacao_movimentos_operacionais_empresa_file_hash",
        table_name="lotes_importacao_movimentos_operacionais",
    )
    op.drop_index(
        op.f("ix_lotes_importacao_movimentos_operacionais_empresa_id"),
        table_name="lotes_importacao_movimentos_operacionais",
    )
    op.drop_table("lotes_importacao_movimentos_operacionais")
