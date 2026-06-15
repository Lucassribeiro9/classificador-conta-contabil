"""add razao import models

Revision ID: 9d1e7a4c2b8f
Revises: 8c3b9d2e4f10
Create Date: 2026-06-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d1e7a4c2b8f"
down_revision: Union[str, Sequence[str], None] = "8c3b9d2e4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lotes_importacao_razao",
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
            name="ck_lotes_importacao_razao_status",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lotes_importacao_razao_empresa_id"),
        "lotes_importacao_razao",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        "ix_lotes_importacao_razao_empresa_file_hash",
        "lotes_importacao_razao",
        ["empresa_id", "file_hash"],
        unique=False,
    )

    op.create_table(
        "lancamentos_razao_normalizados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("numero_lancamento", sa.String(length=50), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("conta_origem", sa.Integer(), nullable=False),
        sa.Column("conta_contrapartida", sa.Integer(), nullable=False),
        sa.Column("conta_debito", sa.Integer(), nullable=False),
        sa.Column("conta_credito", sa.Integer(), nullable=False),
        sa.Column("direcao", sa.String(length=10), nullable=False),
        sa.Column("historico", sa.String(), nullable=False),
        sa.Column("historico_normalizado", sa.String(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "direcao IN ('debito', 'credito')",
            name="ck_lancamentos_razao_normalizados_direcao",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lotes_importacao_razao.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lancamentos_razao_normalizados_empresa_id"),
        "lancamentos_razao_normalizados",
        ["empresa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lancamentos_razao_normalizados_lote_id"),
        "lancamentos_razao_normalizados",
        ["lote_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_lancamentos_razao_normalizados_lote_id"),
        table_name="lancamentos_razao_normalizados",
    )
    op.drop_index(
        op.f("ix_lancamentos_razao_normalizados_empresa_id"),
        table_name="lancamentos_razao_normalizados",
    )
    op.drop_table("lancamentos_razao_normalizados")
    op.drop_index(
        "ix_lotes_importacao_razao_empresa_file_hash",
        table_name="lotes_importacao_razao",
    )
    op.drop_index(
        op.f("ix_lotes_importacao_razao_empresa_id"),
        table_name="lotes_importacao_razao",
    )
    op.drop_table("lotes_importacao_razao")
