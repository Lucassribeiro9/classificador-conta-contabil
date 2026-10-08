"""Confirmed Razão aliases scoped to one company snapshot.

Revision ID: 502a6e1c9d40
Revises: 501a7c4e2d90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "502a6e1c9d40"
down_revision: Union[str, Sequence[str], None] = "501a7c4e2d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_plano_snapshot_entry_company_code",
        "plano_contas_snapshot_entries",
        ["snapshot_id", "empresa_id", "codigo"],
    )
    op.create_table(
        "razao_account_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("observed_code", sa.Integer(), nullable=False),
        sa.Column("target_codigo", sa.Integer(), nullable=False),
        sa.Column("review_item_id", sa.Integer(), sa.ForeignKey("review_items.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "empresa_id", "snapshot_id", "observed_code",
            name="uq_razao_alias_company_snapshot_code",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_razao_alias_snapshot_company",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "empresa_id", "target_codigo"],
            [
                "plano_contas_snapshot_entries.snapshot_id",
                "plano_contas_snapshot_entries.empresa_id",
                "plano_contas_snapshot_entries.codigo",
            ],
            name="fk_razao_alias_target_snapshot_entry",
        ),
    )


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT 1 FROM razao_account_aliases LIMIT 1")).first():
        raise RuntimeError("Confirmed aliases exist; export and approve recovery before downgrade")
    op.drop_table("razao_account_aliases")
    op.drop_constraint(
        "uq_plano_snapshot_entry_company_code",
        "plano_contas_snapshot_entries",
        type_="unique",
    )
