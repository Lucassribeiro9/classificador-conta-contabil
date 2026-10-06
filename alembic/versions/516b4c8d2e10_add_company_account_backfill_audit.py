"""Persist auditable company-account backfill runs and item ownership.

Revision ID: 516b4c8d2e10
Revises: 3c2f6a499e01
Create Date: 2026-10-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "516b4c8d2e10"
down_revision: Union[str, Sequence[str], None] = "3c2f6a499e01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backfill_contas_contabeis_execucoes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'partial', 'rolled_back', 'rollback_partial')",
            name="ck_backfill_contas_contabeis_execucoes_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backfill_contas_contabeis_itens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("execucao_id", sa.String(length=36), nullable=False),
        sa.Column("vinculo_legado_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("conta_codigo", sa.Integer(), nullable=False),
        sa.Column("identidade_id", sa.Integer(), nullable=True),
        sa.Column("resultado", sa.String(length=24), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("target_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("rollback_status", sa.String(length=24), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "resultado IN ('created', 'already_present', 'conflict', 'ineligible', 'failed')",
            name="ck_backfill_contas_contabeis_itens_resultado",
        ),
        sa.CheckConstraint(
            "rollback_status IS NULL OR rollback_status IN ('rolled_back', 'blocked')",
            name="ck_backfill_contas_contabeis_itens_rollback_status",
        ),
        sa.ForeignKeyConstraint(
            ["execucao_id"], ["backfill_contas_contabeis_execucoes.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_backfill_contas_contabeis_itens_execucao_vinculo",
        "backfill_contas_contabeis_itens",
        ["execucao_id", "vinculo_legado_id"],
        unique=True,
    )
    op.create_index(
        "ix_backfill_contas_contabeis_itens_identidade",
        "backfill_contas_contabeis_itens",
        ["identidade_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT 1 FROM backfill_contas_contabeis_itens "
            "WHERE resultado = 'created' "
            "AND (rollback_status IS NULL OR rollback_status = 'blocked') LIMIT 1"
        )
    ).first():
        raise RuntimeError(
            "Downgrade bloqueado: existem identidades criadas por backfill; "
            "execute e valide o rollback antes de remover a trilha de auditoria."
        )
    op.drop_index(
        "ix_backfill_contas_contabeis_itens_identidade",
        table_name="backfill_contas_contabeis_itens",
    )
    op.drop_index(
        "uq_backfill_contas_contabeis_itens_execucao_vinculo",
        table_name="backfill_contas_contabeis_itens",
    )
    op.drop_table("backfill_contas_contabeis_itens")
    op.drop_table("backfill_contas_contabeis_execucoes")
