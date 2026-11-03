"""Persist immutable dataset composition manifests.

Revision ID: 504a7e1c9d40
Revises: 502a6e1c9d40
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "504a7e1c9d40"
down_revision: Union[str, Sequence[str], None] = "502a6e1c9d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("linha_original", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "dataset_manifests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dataset_manifests_empresa_id", "dataset_manifests", ["empresa_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION deny_dataset_manifest_change() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'dataset manifest is immutable';
            END;
            $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER dataset_manifest_immutable
            BEFORE UPDATE OR DELETE ON dataset_manifests
            FOR EACH ROW EXECUTE FUNCTION deny_dataset_manifest_change()
        """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER dataset_manifest_immutable ON dataset_manifests")
        op.execute("DROP FUNCTION deny_dataset_manifest_change()")
    op.drop_index("ix_dataset_manifests_empresa_id", table_name="dataset_manifests")
    op.drop_table("dataset_manifests")
    op.drop_column("lancamentos_razao_normalizados", "linha_original")
