"""add empresa contas contabeis

Revision ID: b4f2a1c9d8e7
Revises: 9d1e7a4c2b8f
Create Date: 2026-06-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4f2a1c9d8e7"
down_revision: Union[str, Sequence[str], None] = "9d1e7a4c2b8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "empresa_contas_contabeis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("conta_codigo", sa.Integer(), nullable=False),
        sa.Column("quantidade_lancamentos", sa.Integer(), nullable=False),
        sa.Column("ultima_utilizacao", sa.Date(), nullable=False),
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
        sa.ForeignKeyConstraint(["conta_codigo"], ["contas_contabeis.codigo"]),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_empresa_contas_contabeis_empresa_conta",
        "empresa_contas_contabeis",
        ["empresa_id", "conta_codigo"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_empresa_contas_contabeis_empresa_conta",
        table_name="empresa_contas_contabeis",
    )
    op.drop_table("empresa_contas_contabeis")
