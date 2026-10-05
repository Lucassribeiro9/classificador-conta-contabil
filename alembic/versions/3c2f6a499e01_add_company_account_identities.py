"""Add company-scoped accounting identities beside the legacy catalog.

Revision ID: 3c2f6a499e01
Revises: 8e4f1a2b3c5d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c2f6a499e01"
down_revision: Union[str, Sequence[str], None] = "8e4f1a2b3c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contas_contabeis_empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.Integer(), nullable=False),
        sa.Column("classificacao", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=1), nullable=False),
        sa.Column("grau", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "is_financial_origin", sa.Boolean(), server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tipo IN ('A', 'S')", name="ck_contas_contabeis_empresas_tipo"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
    )
    op.create_index(
        "uq_contas_contabeis_empresas_empresa_codigo",
        "contas_contabeis_empresas",
        ["empresa_id", "codigo"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_contas_contabeis_empresas_empresa_codigo",
        table_name="contas_contabeis_empresas",
    )
    op.drop_table("contas_contabeis_empresas")
