"""update operational movement direction constraint

Revision ID: a1b2c3d4e5f6
Revises: e2c4d8f6a9b1
Create Date: 2026-06-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e2c4d8f6a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_movimentos_operacionais_importados_direcao",
        "movimentos_operacionais_importados",
        type_="check",
    )
    op.execute(
        """
        UPDATE movimentos_operacionais_importados
        SET direcao = CASE direcao
            WHEN 'entrada' THEN 'debito'
            WHEN 'saida' THEN 'credito'
            ELSE direcao
        END
        """
    )
    op.create_check_constraint(
        "ck_movimentos_operacionais_importados_direcao",
        "movimentos_operacionais_importados",
        "direcao IN ('debito', 'credito')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_movimentos_operacionais_importados_direcao",
        "movimentos_operacionais_importados",
        type_="check",
    )
    op.execute(
        """
        UPDATE movimentos_operacionais_importados
        SET direcao = CASE direcao
            WHEN 'debito' THEN 'entrada'
            WHEN 'credito' THEN 'saida'
            ELSE direcao
        END
        """
    )
    op.create_check_constraint(
        "ck_movimentos_operacionais_importados_direcao",
        "movimentos_operacionais_importados",
        "direcao IN ('entrada', 'saida')",
    )
