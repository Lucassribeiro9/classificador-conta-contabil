"""Add the company-scoped generic review center.

Revision ID: b8c4d2e6f910
Revises: 517a8d4c2e11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c4d2e6f910"
down_revision: Union[str, Sequence[str], None] = "517a8d4c2e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("grouping_key", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("criticality", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'in_review', 'resolved', 'dismissed')",
            name="ck_review_items_status",
        ),
        sa.CheckConstraint(
            "criticality IN ('low', 'medium', 'high', 'critical')",
            name="ck_review_items_criticality",
        ),
        sa.UniqueConstraint(
            "empresa_id",
            "source_type",
            "grouping_key",
            name="uq_review_items_company_source_group",
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"], ["empresas.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["usuarios.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_review_items_empresa_id", "review_items", ["empresa_id"])
    op.create_index("ix_review_items_assignee_id", "review_items", ["assignee_id"])
    op.create_index(
        "ix_review_items_company_status_criticality_created",
        "review_items",
        ["empresa_id", "status", "criticality", "created_at"],
    )

    op.create_table(
        "review_item_evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_item_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "review_item_id",
            "source_type",
            "source_id",
            name="uq_review_item_evidence_source",
        ),
        sa.ForeignKeyConstraint(
            ["review_item_id"], ["review_items.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_review_item_evidences_review_item_id",
        "review_item_evidences",
        ["review_item_id"],
    )

    op.create_table(
        "review_item_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_item_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_item_id"], ["review_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_review_item_events_review_item_id",
        "review_item_events",
        ["review_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_item_events_review_item_id", table_name="review_item_events")
    op.drop_table("review_item_events")
    op.drop_index(
        "ix_review_item_evidences_review_item_id", table_name="review_item_evidences"
    )
    op.drop_table("review_item_evidences")
    op.drop_index(
        "ix_review_items_company_status_criticality_created", table_name="review_items"
    )
    op.drop_index("ix_review_items_assignee_id", table_name="review_items")
    op.drop_index("ix_review_items_empresa_id", table_name="review_items")
    op.drop_table("review_items")
