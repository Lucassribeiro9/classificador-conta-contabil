"""add unique dedup index to transactions

Revision ID: 7a5b1449dbb5
Revises: 5e7c9d3a1b2f
Create Date: 2026-04-28 17:48:12.731479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a5b1449dbb5'
down_revision: Union[str, Sequence[str], None] = '5e7c9d3a1b2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM transacoes
        WHERE id IN (
          SELECT id
          FROM (
            SELECT
              id,
              ROW_NUMBER() OVER (
                PARTITION BY
                  empresa_id,
                  data,
                  historico,
                  valor,
                  COALESCE(conta_contabil, -1),
                  COALESCE(cod_banco, -1)
                ORDER BY id
              ) AS duplicate_rank
            FROM transacoes
          )
          WHERE duplicate_rank > 1
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_transacao_dedup
        ON transacoes (
          empresa_id,
          data,
          historico,
          valor,
          COALESCE(conta_contabil, -1),
          COALESCE(cod_banco, -1)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_transacao_dedup")
