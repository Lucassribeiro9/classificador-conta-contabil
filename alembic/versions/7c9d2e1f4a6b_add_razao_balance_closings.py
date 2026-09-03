"""add razao balance closings

Revision ID: 7c9d2e1f4a6b
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c9d2e1f4a6b"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_anterior_original", sa.String(), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column(
            "saldo_anterior_decimal",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_anterior_natureza", sa.String(length=1), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_original", sa.String(), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_decimal", sa.Numeric(precision=14, scale=2), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_natureza", sa.String(length=1), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_exercicio_original", sa.String(), nullable=True),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column(
            "saldo_exercicio_decimal",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "lancamentos_razao_normalizados",
        sa.Column("saldo_exercicio_natureza", sa.String(length=1), nullable=True),
    )
    op.create_check_constraint(
        "ck_lancamentos_razao_normalizados_saldo_anterior_natureza",
        "lancamentos_razao_normalizados",
        "saldo_anterior_natureza IS NULL OR saldo_anterior_natureza IN ('D', 'C')",
    )
    op.create_check_constraint(
        "ck_lancamentos_razao_normalizados_saldo_natureza",
        "lancamentos_razao_normalizados",
        "saldo_natureza IS NULL OR saldo_natureza IN ('D', 'C')",
    )
    op.create_check_constraint(
        "ck_lancamentos_razao_normalizados_saldo_exercicio_natureza",
        "lancamentos_razao_normalizados",
        "saldo_exercicio_natureza IS NULL OR saldo_exercicio_natureza IN ('D', 'C')",
    )

    op.create_table(
        "fechamentos_razao_mensais",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("conta_codigo", sa.Integer(), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("saldo_observado_original", sa.String(), nullable=True),
        sa.Column(
            "saldo_observado_decimal",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column("saldo_observado_natureza", sa.String(length=1), nullable=True),
        sa.Column("saldo_observado_fonte", sa.String(length=30), nullable=True),
        sa.Column(
            "saldo_calculado_decimal",
            sa.Numeric(precision=14, scale=2),
            nullable=True,
        ),
        sa.Column("warnings_saldo", sa.JSON(), server_default="[]", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mes >= 1 AND mes <= 12",
            name="ck_fechamentos_razao_mensais_mes",
        ),
        sa.CheckConstraint(
            "saldo_observado_natureza IS NULL OR saldo_observado_natureza IN ('D', 'C')",
            name="ck_fechamentos_razao_mensais_saldo_observado_natureza",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["lote_id"], ["lotes_importacao_razao.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "empresa_id",
            "conta_codigo",
            "ano",
            "mes",
            "lote_id",
            name="uq_fechamentos_razao_mensais_empresa_conta_mes_lote",
        ),
    )
    op.create_index(
        "ix_fechamentos_razao_mensais_empresa_conta_mes",
        "fechamentos_razao_mensais",
        ["empresa_id", "conta_codigo", "ano", "mes"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fechamentos_razao_mensais_lote_id"),
        "fechamentos_razao_mensais",
        ["lote_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_fechamentos_razao_mensais_lote_id"),
        table_name="fechamentos_razao_mensais",
    )
    op.drop_index(
        "ix_fechamentos_razao_mensais_empresa_conta_mes",
        table_name="fechamentos_razao_mensais",
    )
    op.drop_table("fechamentos_razao_mensais")
    op.drop_constraint(
        "ck_lancamentos_razao_normalizados_saldo_exercicio_natureza",
        "lancamentos_razao_normalizados",
        type_="check",
    )
    op.drop_constraint(
        "ck_lancamentos_razao_normalizados_saldo_natureza",
        "lancamentos_razao_normalizados",
        type_="check",
    )
    op.drop_constraint(
        "ck_lancamentos_razao_normalizados_saldo_anterior_natureza",
        "lancamentos_razao_normalizados",
        type_="check",
    )
    op.drop_column("lancamentos_razao_normalizados", "saldo_exercicio_natureza")
    op.drop_column("lancamentos_razao_normalizados", "saldo_exercicio_decimal")
    op.drop_column("lancamentos_razao_normalizados", "saldo_exercicio_original")
    op.drop_column("lancamentos_razao_normalizados", "saldo_natureza")
    op.drop_column("lancamentos_razao_normalizados", "saldo_decimal")
    op.drop_column("lancamentos_razao_normalizados", "saldo_original")
    op.drop_column("lancamentos_razao_normalizados", "saldo_anterior_natureza")
    op.drop_column("lancamentos_razao_normalizados", "saldo_anterior_decimal")
    op.drop_column("lancamentos_razao_normalizados", "saldo_anterior_original")
