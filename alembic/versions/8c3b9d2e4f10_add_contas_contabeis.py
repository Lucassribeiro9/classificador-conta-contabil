"""add contas contabeis

Revision ID: 8c3b9d2e4f10
Revises: 4d9f2a8c1e6b
Create Date: 2026-06-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8c3b9d2e4f10"
down_revision: Union[str, Sequence[str], None] = "4d9f2a8c1e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contas_contabeis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.Integer(), nullable=False),
        sa.Column("classificacao", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=1), nullable=False),
        sa.Column("grau", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_financial_origin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "tipo IN ('A', 'S')",
            name="ck_contas_contabeis_tipo",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contas_contabeis_codigo"),
        "contas_contabeis",
        ["codigo"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_contas_contabeis_codigo"), table_name="contas_contabeis")
    op.drop_table("contas_contabeis")
