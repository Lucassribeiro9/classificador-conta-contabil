"""add operational snapshot version fields

Revision ID: f3a9c1d7e2b4
Revises: a1b2c3d4e5f6
Create Date: 2026-08-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a9c1d7e2b4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lotes_importacao_movimentos_operacionais",
        sa.Column(
            "layout_version",
            sa.String(length=80),
            server_default="operacional_valor_legado_v1",
            nullable=False,
        ),
    )
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column("linha_original", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("movimentos_operacionais_importados", "row_version")
    op.drop_column("movimentos_operacionais_importados", "linha_original")
    op.drop_column("lotes_importacao_movimentos_operacionais", "layout_version")
