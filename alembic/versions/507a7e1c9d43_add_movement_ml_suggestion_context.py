"""Persist the reviewed ML suggestion context for operational movements.

Revision ID: 507a7e1c9d43
Revises: 506a7e1c9d42
"""

from alembic import op
import sqlalchemy as sa

revision = "507a7e1c9d43"
down_revision = "506a7e1c9d42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "movimentos_operacionais_importados",
        sa.Column("ml_suggestion_context", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("movimentos_operacionais_importados", "ml_suggestion_context")
