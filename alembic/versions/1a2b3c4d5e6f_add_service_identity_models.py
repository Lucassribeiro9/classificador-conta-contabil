"""add service identity models

Revision ID: 1a2b3c4d5e6f
Revises: 6b1c2d3e4f5a
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "6b1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identidades_servico",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("credential_hash", sa.String(length=255), nullable=False),
        sa.Column("credential_fingerprint", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ativa",
        ),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
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
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('ativa', 'inativa', 'revogada')",
            name="ck_identidades_servico_status",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_identidades_servico_identifier"),
        "identidades_servico",
        ["identifier"],
        unique=True,
    )
    op.create_index(
        op.f("ix_identidades_servico_credential_fingerprint"),
        "identidades_servico",
        ["credential_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_identidades_servico_status",
        "identidades_servico",
        ["status"],
        unique=False,
    )

    op.create_table(
        "identidade_servico_empresas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identidade_servico_id", sa.Integer(), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["empresa_id"],
            ["empresas.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["identidade_servico_id"],
            ["identidades_servico.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_identidade_servico_empresas_identidade_empresa",
        "identidade_servico_empresas",
        ["identidade_servico_id", "empresa_id"],
        unique=True,
    )
    op.create_index(
        "ix_identidade_servico_empresas_empresa",
        "identidade_servico_empresas",
        ["empresa_id"],
        unique=False,
    )

    op.create_table(
        "identidade_servico_escopos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identidade_servico_id", sa.Integer(), nullable=False),
        sa.Column("escopo", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "escopo IN ('empresas:read', 'ml:classificar', "
            "'movimentos:download', 'movimentos:feedback')",
            name="ck_identidade_servico_escopos_escopo",
        ),
        sa.ForeignKeyConstraint(
            ["identidade_servico_id"],
            ["identidades_servico.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_identidade_servico_escopos_identidade_escopo",
        "identidade_servico_escopos",
        ["identidade_servico_id", "escopo"],
        unique=True,
    )
    op.create_index(
        "ix_identidade_servico_escopos_escopo",
        "identidade_servico_escopos",
        ["escopo"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identidade_servico_escopos_escopo",
        table_name="identidade_servico_escopos",
    )
    op.drop_index(
        "uq_identidade_servico_escopos_identidade_escopo",
        table_name="identidade_servico_escopos",
    )
    op.drop_table("identidade_servico_escopos")
    op.drop_index(
        "ix_identidade_servico_empresas_empresa",
        table_name="identidade_servico_empresas",
    )
    op.drop_index(
        "uq_identidade_servico_empresas_identidade_empresa",
        table_name="identidade_servico_empresas",
    )
    op.drop_table("identidade_servico_empresas")
    op.drop_index("ix_identidades_servico_status", table_name="identidades_servico")
    op.drop_index(
        op.f("ix_identidades_servico_credential_fingerprint"),
        table_name="identidades_servico",
    )
    op.drop_index(
        op.f("ix_identidades_servico_identifier"),
        table_name="identidades_servico",
    )
    op.drop_table("identidades_servico")
