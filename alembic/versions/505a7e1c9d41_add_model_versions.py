"""Add immutable model evidence and one-active-per-company constraint.

Revision ID: 505a7e1c9d41
Revises: 504a7e1c9d40
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "505a7e1c9d41"
down_revision: Union[str, Sequence[str], None] = "504a7e1c9d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "empresas",
        sa.Column("ml_critical_classes", sa.JSON(), server_default="[]", nullable=False),
    )
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("manifest_id", sa.Integer(), sa.ForeignKey("dataset_manifests.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("artifact_path", sa.String(255), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("critical_classes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('candidate', 'active', 'retired')", name="ck_model_versions_status"),
    )
    op.create_index("ix_model_versions_empresa_id", "model_versions", ["empresa_id"])
    op.create_index(
        "uq_model_versions_one_active_per_company", "model_versions", ["empresa_id"],
        unique=True, postgresql_where=sa.text("status = 'active'"), sqlite_where=sa.text("status = 'active'"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION deny_model_version_evidence_change() RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'model version evidence is immutable';
                END IF;
                IF OLD.artifact_path = '' AND OLD.artifact_sha256 = ''
                   AND NEW.artifact_path = format('empresa_%s/model_%s.joblib', OLD.empresa_id, OLD.id)
                   AND length(NEW.artifact_sha256) = 64
                   AND NEW.empresa_id IS NOT DISTINCT FROM OLD.empresa_id
                   AND NEW.manifest_id IS NOT DISTINCT FROM OLD.manifest_id
                   AND NEW.status IS NOT DISTINCT FROM OLD.status
                   AND NEW.threshold IS NOT DISTINCT FROM OLD.threshold
                   AND NEW.metrics::text IS NOT DISTINCT FROM OLD.metrics::text
                   AND NEW.evaluation::text IS NOT DISTINCT FROM OLD.evaluation::text
                   AND NEW.critical_classes::text IS NOT DISTINCT FROM OLD.critical_classes::text
                   AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at THEN
                    RETURN NEW;
                END IF;
                IF NEW.empresa_id IS DISTINCT FROM OLD.empresa_id
                   OR NEW.manifest_id IS DISTINCT FROM OLD.manifest_id
                   OR NEW.artifact_path IS DISTINCT FROM OLD.artifact_path
                   OR NEW.artifact_sha256 IS DISTINCT FROM OLD.artifact_sha256
                   OR NEW.threshold IS DISTINCT FROM OLD.threshold
                   OR NEW.metrics::text IS DISTINCT FROM OLD.metrics::text
                   OR NEW.evaluation::text IS DISTINCT FROM OLD.evaluation::text
                   OR NEW.critical_classes::text IS DISTINCT FROM OLD.critical_classes::text
                   OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                    RAISE EXCEPTION 'model version evidence is immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER model_version_evidence_immutable
            BEFORE UPDATE OR DELETE ON model_versions
            FOR EACH ROW EXECUTE FUNCTION deny_model_version_evidence_change()
        """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER model_version_evidence_immutable ON model_versions")
        op.execute("DROP FUNCTION deny_model_version_evidence_change()")
    op.drop_index("uq_model_versions_one_active_per_company", table_name="model_versions")
    op.drop_index("ix_model_versions_empresa_id", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_column("empresas", "ml_critical_classes")
