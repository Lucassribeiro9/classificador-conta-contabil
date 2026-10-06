"""Link legacy company-account usage to the stable company identity.

Revision ID: 517a8d4c2e11
Revises: 516b4c8d2e10
Create Date: 2026-10-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "517a8d4c2e11"
down_revision: Union[str, Sequence[str], None] = "516b4c8d2e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "empresa_contas_contabeis",
        sa.Column("conta_contabil_empresa_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_contas_contabeis_empresas_id_empresa",
        "contas_contabeis_empresas",
        ["id", "empresa_id"],
    )
    op.create_foreign_key(
        "fk_empresa_contas_contabeis_identidade_empresa",
        "empresa_contas_contabeis",
        "contas_contabeis_empresas",
        ["conta_contabil_empresa_id", "empresa_id"],
        ["id", "empresa_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_empresa_contas_contabeis_conta_contabil_empresa_id",
        "empresa_contas_contabeis",
        ["conta_contabil_empresa_id"],
        unique=False,
    )
    op.execute(
        sa.text(
            "UPDATE empresa_contas_contabeis AS vinculo "
            "SET conta_contabil_empresa_id = identidade.id "
            "FROM contas_contabeis_empresas AS identidade "
            "WHERE identidade.empresa_id = vinculo.empresa_id "
            "AND identidade.codigo = vinculo.conta_codigo"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_empresa_contas_contabeis_conta_contabil_empresa_id",
        table_name="empresa_contas_contabeis",
    )
    op.drop_constraint(
        "fk_empresa_contas_contabeis_identidade_empresa",
        "empresa_contas_contabeis",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_contas_contabeis_empresas_id_empresa",
        "contas_contabeis_empresas",
        type_="unique",
    )
    op.drop_column("empresa_contas_contabeis", "conta_contabil_empresa_id")
