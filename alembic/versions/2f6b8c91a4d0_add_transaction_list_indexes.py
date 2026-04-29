"""add transaction list indexes

Revision ID: 2f6b8c91a4d0
Revises: 7a5b1449dbb5
Create Date: 2026-04-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2f6b8c91a4d0"
down_revision: Union[str, Sequence[str], None] = "7a5b1449dbb5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_transacoes_empresa_id_id",
        "transacoes",
        ["empresa_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_transacoes_empresa_data_banco_conta",
        "transacoes",
        ["empresa_id", "data", "cod_banco", "conta_contabil", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transacoes_empresa_data_banco_conta", table_name="transacoes")
    op.drop_index("ix_transacoes_empresa_id_id", table_name="transacoes")
