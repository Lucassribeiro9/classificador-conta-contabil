"""add razao async jobs and normalized warnings

Revision ID: 8e4f1a2b3c5d
Revises: 7c9d2e1f4a6b
Create Date: 2026-09-09 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8e4f1a2b3c5d"
down_revision: Union[str, Sequence[str], None] = "7c9d2e1f4a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _duplicate_lot_ids(connection: sa.Connection) -> list[list[int]]:
    rows = connection.execute(
        sa.text(
            """
            SELECT array_agg(id ORDER BY id) AS lote_ids
            FROM lotes_importacao_razao
            GROUP BY empresa_id, file_hash
            HAVING count(*) > 1
            ORDER BY min(id)
            """
        )
    )
    return [list(row.lote_ids) for row in rows]


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = _duplicate_lot_ids(connection)
    if duplicates:
        raise RuntimeError(
            "Migration bloqueada: lotes duplicados por empresa/hash: "
            f"{duplicates}. Resolva os grupos sem apagar dados silenciosamente."
        )

    op.drop_constraint(
        "ck_lotes_importacao_razao_status",
        "lotes_importacao_razao",
        type_="check",
    )
    op.drop_index(
        "ix_lotes_importacao_razao_empresa_file_hash",
        table_name="lotes_importacao_razao",
    )
    op.alter_column("lotes_importacao_razao", "usuario_id", nullable=True)
    op.alter_column("lotes_importacao_razao", "total_linhas", nullable=True)
    op.alter_column(
        "lotes_importacao_razao",
        "warnings_metadata",
        server_default=sa.text("'{\"totals_by_code\": {}}'::json"),
    )
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("identidade_servico_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("linhas_processadas", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("warnings_total", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("lotes_importacao_razao", sa.Column("lease_token", sa.String(36)))
    op.add_column("lotes_importacao_razao", sa.Column("lease_owner", sa.String(255)))
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "lotes_importacao_razao",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    )
    op.add_column("lotes_importacao_razao", sa.Column("error_code", sa.String(80)))
    op.add_column("lotes_importacao_razao", sa.Column("error_message", sa.String(500)))
    op.add_column(
        "lotes_importacao_razao", sa.Column("error_request_id", sa.String(80))
    )
    op.add_column(
        "lotes_importacao_razao", sa.Column("failed_at", sa.DateTime(timezone=True))
    )
    op.execute(
        sa.text(
            """
            UPDATE lotes_importacao_razao
            SET attempt_count = 1,
                linhas_processadas = COALESCE(total_linhas, 0)
            """
        )
    )
    op.create_foreign_key(
        "fk_lotes_importacao_razao_identidade_servico",
        "lotes_importacao_razao",
        "identidades_servico",
        ["identidade_servico_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_status",
        "lotes_importacao_razao",
        "status IN ('queued', 'processing', 'completed', 'completed_with_warnings', 'failed')",
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_total_linhas",
        "lotes_importacao_razao",
        "total_linhas IS NULL OR total_linhas >= 0",
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_contadores_nao_negativos",
        "lotes_importacao_razao",
        "linhas_processadas >= 0 AND total_importadas >= 0 AND total_invalidas >= 0 AND warnings_total >= 0",
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_processadas_ate_total",
        "lotes_importacao_razao",
        "total_linhas IS NULL OR linhas_processadas <= total_linhas",
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_resultados_ate_processadas",
        "lotes_importacao_razao",
        "(status IN ('queued', 'processing') AND total_importadas + total_invalidas <= linhas_processadas) OR "
        "(status IN ('completed', 'completed_with_warnings', 'failed') AND "
        "((total_linhas IS NULL AND total_importadas = 0 AND total_invalidas = 0) OR "
        "(total_linhas IS NOT NULL AND total_importadas + total_invalidas <= total_linhas)))",
    )
    op.create_check_constraint(
        "ck_lotes_importacao_razao_solicitante",
        "lotes_importacao_razao",
        "(usuario_id IS NOT NULL AND identidade_servico_id IS NULL) OR "
        "(usuario_id IS NULL AND identidade_servico_id IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_lotes_importacao_razao_empresa_file_hash",
        "lotes_importacao_razao",
        ["empresa_id", "file_hash"],
    )

    op.create_table(
        "tentativas_importacao_razao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("resultado", sa.String(40)),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.String(500)),
        sa.Column("error_request_id", sa.String(80)),
        sa.CheckConstraint(
            "resultado IS NULL OR resultado IN ('completed', 'completed_with_warnings', 'failed', 'interrupted')",
            name="ck_tentativas_importacao_razao_resultado",
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lotes_importacao_razao.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "lote_id", "numero", name="uq_tentativas_importacao_razao_lote_numero"
        ),
    )
    op.create_index(
        "ix_tentativas_importacao_razao_lote_id",
        "tentativas_importacao_razao",
        ["lote_id"],
    )
    op.create_table(
        "warnings_importacao_razao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("linha", sa.Integer()),
        sa.Column("codigo", sa.String(80), nullable=False),
        sa.Column("mensagem", sa.String(500), nullable=False),
        sa.Column("detalhes", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lotes_importacao_razao.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_warnings_importacao_razao_lote_id_id",
        "warnings_importacao_razao",
        ["lote_id", "id"],
    )
    op.create_index(
        "ix_warnings_importacao_razao_lote_codigo_linha",
        "warnings_importacao_razao",
        ["lote_id", "codigo", "linha"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    incompatible = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM lotes_importacao_razao
                WHERE status = 'queued'
                   OR total_linhas IS NULL
                   OR identidade_servico_id IS NOT NULL
            ) OR EXISTS (SELECT 1 FROM tentativas_importacao_razao)
              OR EXISTS (SELECT 1 FROM warnings_importacao_razao)
            """
        )
    ).scalar_one()
    if incompatible:
        raise RuntimeError(
            "Downgrade bloqueado: existem dados assincronos incompativeis com o schema anterior."
        )

    op.drop_index("ix_warnings_importacao_razao_lote_codigo_linha", table_name="warnings_importacao_razao")
    op.drop_index("ix_warnings_importacao_razao_lote_id_id", table_name="warnings_importacao_razao")
    op.drop_table("warnings_importacao_razao")
    op.drop_index("ix_tentativas_importacao_razao_lote_id", table_name="tentativas_importacao_razao")
    op.drop_table("tentativas_importacao_razao")
    op.drop_constraint("uq_lotes_importacao_razao_empresa_file_hash", "lotes_importacao_razao", type_="unique")
    for name in (
        "ck_lotes_importacao_razao_solicitante",
        "ck_lotes_importacao_razao_resultados_ate_processadas",
        "ck_lotes_importacao_razao_processadas_ate_total",
        "ck_lotes_importacao_razao_contadores_nao_negativos",
        "ck_lotes_importacao_razao_total_linhas",
        "ck_lotes_importacao_razao_status",
    ):
        op.drop_constraint(name, "lotes_importacao_razao", type_="check")
    op.drop_constraint("fk_lotes_importacao_razao_identidade_servico", "lotes_importacao_razao", type_="foreignkey")
    for column in (
        "failed_at", "error_request_id", "error_message", "error_code",
        "heartbeat_at", "lease_expires_at", "lease_owner", "lease_token",
        "attempt_count", "warnings_total", "linhas_processadas", "identidade_servico_id",
    ):
        op.drop_column("lotes_importacao_razao", column)
    op.alter_column("lotes_importacao_razao", "total_linhas", nullable=False)
    op.alter_column(
        "lotes_importacao_razao",
        "warnings_metadata",
        server_default=sa.text("'{}'::json"),
    )
    op.alter_column("lotes_importacao_razao", "usuario_id", nullable=False)
    op.create_check_constraint(
        "ck_lotes_importacao_razao_status",
        "lotes_importacao_razao",
        "status IN ('processing', 'completed', 'completed_with_warnings', 'failed')",
    )
    op.create_index(
        "ix_lotes_importacao_razao_empresa_file_hash",
        "lotes_importacao_razao",
        ["empresa_id", "file_hash"],
    )
