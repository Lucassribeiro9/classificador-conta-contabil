"""add operational balance fields

Revision ID: 6b1c2d3e4f5a
Revises: f3a9c1d7e2b4
Create Date: 2026-08-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "f3a9c1d7e2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column("saldo_observado_original", sa.String(), nullable=True),
    )
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column(
            "saldo_observado_decimal",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column(
            "saldo_calculado_decimal",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column("warnings_saldo", sa.JSON(), server_default="[]", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("movimentos_operacionais_importados", "warnings_saldo")
    op.drop_column("movimentos_operacionais_importados", "saldo_calculado_decimal")
    op.drop_column("movimentos_operacionais_importados", "saldo_observado_decimal")
    op.drop_column("movimentos_operacionais_importados", "saldo_observado_original")
