"""sync schema

Revision ID: 1254be5f9012
Revises:
Create Date: 2026-02-22 16:37:37.317457

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1254be5f9012"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_empresa", sa.String(length=100), nullable=False),
        sa.Column("api_key", sa.String(length=70), nullable=False),
        sa.Column("cnpj_cpf", sa.String(length=15), nullable=False),  # baseline antigo
        sa.Column("cod_dominio", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cod_dominio"),
    )
    op.create_index(op.f("ix_empresas_api_key"), "empresas", ["api_key"], unique=True)
    op.create_index(op.f("ix_empresas_cnpj_cpf"), "empresas", ["cnpj_cpf"], unique=True)
    op.create_index(op.f("ix_empresas_id"), "empresas", ["id"], unique=False)

    op.create_table(
        "transacoes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("cod_banco", sa.Integer(), nullable=True),
        sa.Column("historico", sa.String(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("conta_contabil", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("is_classified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("transacoes")
    op.drop_index(op.f("ix_empresas_id"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_cnpj_cpf"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_api_key"), table_name="empresas")
    op.drop_table("empresas")
