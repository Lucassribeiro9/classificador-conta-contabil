"""Company plan snapshots, import events, entries and reviewed decisions.

Revision ID: 501a7c4e2d90
Revises: b8c4d2e6f910
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "501a7c4e2d90"
down_revision: Union[str, Sequence[str], None] = "b8c4d2e6f910"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plano_contas_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "empresa_id", "content_hash", name="uq_plano_snapshot_content"
        ),
        sa.UniqueConstraint("id", "empresa_id", name="uq_plano_snapshot_id_company"),
    )
    op.create_table(
        "plano_contas_import_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False
        ),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("vigencia", sa.Date(), nullable=False),
        sa.Column("vigencia_inferida", sa.Boolean(), nullable=False),
        sa.Column("origem", sa.String(255), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_import_snapshot_company",
        ),
    )
    op.create_index(
        "ix_plano_import_company_date",
        "plano_contas_import_events",
        ["empresa_id", "vigencia"],
    )
    op.create_table(
        "plano_contas_snapshot_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column(
            "empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False
        ),
        sa.Column("conta_contabil_empresa_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.Integer(), nullable=False),
        sa.Column("classificacao", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("tipo", sa.String(1), nullable=False),
        sa.Column("grau", sa.Integer(), nullable=False),
        sa.CheckConstraint("tipo IN ('A', 'S')", name="ck_plano_snapshot_entry_tipo"),
        sa.UniqueConstraint(
            "snapshot_id", "codigo", name="uq_plano_snapshot_entry_code"
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_snapshot_entry_snapshot_company",
        ),
        sa.ForeignKeyConstraint(
            ["conta_contabil_empresa_id", "empresa_id"],
            ["contas_contabeis_empresas.id", "contas_contabeis_empresas.empresa_id"],
            name="fk_plano_snapshot_entry_identity_company",
        ),
    )
    op.create_table(
        "plano_contas_conflict_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False
        ),
        sa.Column("vigencia", sa.Date(), nullable=False),
        sa.Column("candidate_hash", sa.String(64), nullable=False),
        sa.Column(
            "review_item_id",
            sa.Integer(),
            sa.ForeignKey("review_items.id"),
            nullable=False,
        ),
        sa.Column("selected_snapshot_id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False
        ),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "empresa_id",
            "vigencia",
            "candidate_hash",
            name="uq_plano_conflict_decision_candidates",
        ),
        sa.ForeignKeyConstraint(
            ["selected_snapshot_id", "empresa_id"],
            ["plano_contas_snapshots.id", "plano_contas_snapshots.empresa_id"],
            name="fk_plano_decision_snapshot_company",
        ),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION reject_plan_snapshot_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Temporal plan history is immutable';
            END;
            $$ LANGUAGE plpgsql
        """)
        for table in (
            "plano_contas_snapshots",
            "plano_contas_snapshot_entries",
            "plano_contas_import_events",
            "plano_contas_conflict_decisions",
        ):
            op.execute(
                sa.text(
                    f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                    "FOR EACH ROW EXECUTE FUNCTION reject_plan_snapshot_mutation()"
                )
            )


def downgrade() -> None:
    for table in (
        "plano_contas_snapshots",
        "plano_contas_import_events",
        "plano_contas_snapshot_entries",
        "plano_contas_conflict_decisions",
    ):
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError(
                "Snapshot history exists; export and approve a recovery plan before downgrade"
            )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_plan_snapshot_mutation() CASCADE")
    op.drop_table("plano_contas_conflict_decisions")
    op.drop_table("plano_contas_snapshot_entries")
    op.drop_index(
        "ix_plano_import_company_date", table_name="plano_contas_import_events"
    )
    op.drop_table("plano_contas_import_events")
    op.drop_table("plano_contas_snapshots")
