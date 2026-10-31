"""versao_dados: contador que o cache da API usa para saber se os dados mudaram

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "versao_dados",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("contador", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("id = 1", name=op.f("ck_versao_dados_linha_unica")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_versao_dados")),
    )
    op.execute("INSERT INTO versao_dados (id, contador) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("versao_dados")
