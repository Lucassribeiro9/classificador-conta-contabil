"""Durable ML jobs with per-company idempotency and exclusive execution.

Revision ID: 506a7e1c9d42
Revises: 505a7e1c9d41
"""

from alembic import op
import sqlalchemy as sa

revision = "506a7e1c9d42"
down_revision = "505a7e1c9d41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("usuarios.id")),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("pool", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("lease_owner", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime()),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result", sa.JSON()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('train', 'classify', 'classify_movements')", name="ck_ml_jobs_kind"),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')", name="ck_ml_jobs_status"),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="ck_ml_jobs_progress"),
        sa.CheckConstraint("attempts >= 0", name="ck_ml_jobs_attempts"),
        sa.CheckConstraint(
            "(status = 'running' AND lease_token IS NOT NULL AND lease_owner IS NOT NULL "
            "AND lease_expires_at IS NOT NULL) OR "
            "(status <> 'running' AND lease_token IS NULL AND lease_owner IS NULL "
            "AND lease_expires_at IS NULL)",
            name="ck_ml_jobs_lease_state",
        ),
        sa.UniqueConstraint("empresa_id", "idempotency_key", name="uq_ml_jobs_company_key"),
    )
    op.create_index("ix_ml_jobs_empresa_id", "ml_jobs", ["empresa_id"])
    op.create_index(
        "uq_ml_jobs_one_running_per_company", "ml_jobs", ["empresa_id"],
        unique=True, postgresql_where=sa.text("status = 'running'"),
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_ml_jobs_one_running_per_company", table_name="ml_jobs")
    op.drop_index("ix_ml_jobs_empresa_id", table_name="ml_jobs")
    op.drop_table("ml_jobs")
