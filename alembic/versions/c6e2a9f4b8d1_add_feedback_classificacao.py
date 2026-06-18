"""add feedback classificacao

Revision ID: c6e2a9f4b8d1
Revises: b4f2a1c9d8e7
Create Date: 2026-06-18 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6e2a9f4b8d1"
down_revision: Union[str, Sequence[str], None] = "b4f2a1c9d8e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_classificacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("lancamento_id", sa.Integer(), nullable=False),
        sa.Column("conta_sugerida", sa.Integer(), nullable=False),
        sa.Column("conta_final", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["lancamento_id"],
            ["lancamentos_razao_normalizados.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feedback_classificacao_empresa_lancamento",
        "feedback_classificacao",
        ["empresa_id", "lancamento_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feedback_classificacao_empresa_lancamento",
        table_name="feedback_classificacao",
    )
    op.drop_table("feedback_classificacao")
