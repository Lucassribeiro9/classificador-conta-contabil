"""normalize cnpj_cpf digits only

Revision ID: 5e7c9d3a1b2f
Revises: defcb6110a20
Create Date: 2026-03-02 00:00:00.000000

"""

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5e7c9d3a1b2f"
down_revision: Union[str, Sequence[str], None] = "defcb6110a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normaliza cnpj_cpf existentes para conter apenas dígitos."""
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, cnpj_cpf FROM empresas")).fetchall()

    normalized_docs: dict[int, str] = {}
    seen_docs: dict[str, int] = {}

    for row_id, document in rows:
        normalized = re.sub(r"\D", "", document or "")
        if len(normalized) not in (11, 14):
            raise ValueError(
                f"Documento inválido encontrado na migração (id={row_id}): {document}"
            )
        if normalized in seen_docs:
            raise ValueError(
                "Documentos duplicados encontrados após normalização: "
                f"id={seen_docs[normalized]} e id={row_id}"
            )
        seen_docs[normalized] = row_id
        normalized_docs[row_id] = normalized

    for row_id, normalized in normalized_docs.items():
        connection.execute(
            sa.text("UPDATE empresas SET cnpj_cpf = :cnpj_cpf WHERE id = :id"),
            {"cnpj_cpf": normalized, "id": row_id},
        )


def downgrade() -> None:
    """Não há restauração de máscara para cnpj_cpf."""
    return
