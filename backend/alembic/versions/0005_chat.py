"""chat: extensão vector, índice de trechos dos alertas e contagens anônimas

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-01 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "trecho_alerta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alerta_id", sa.Integer(), nullable=False),
        sa.Column("alerta_hash", sa.String(length=64), nullable=False),
        sa.Column("classificacao_id", sa.Integer(), nullable=False),
        sa.Column("posicao", sa.Integer(), nullable=False),
        sa.Column("inicio", sa.Integer(), nullable=False),
        sa.Column("fim", sa.Integer(), nullable=False),
        sa.Column(
            "paises", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column(
            "em_vigor_para",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("modelo_embedding", sa.Text(), nullable=False),
        sa.Column("dimensoes", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.Column("indexado_em", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("fim > inicio", name=op.f("ck_trecho_alerta_intervalo_valido")),
        sa.CheckConstraint("dimensoes > 0", name=op.f("ck_trecho_alerta_dimensoes_positivas")),
        sa.CheckConstraint(
            "vector_dims(embedding) = dimensoes", name=op.f("ck_trecho_alerta_dimensoes_do_vetor")
        ),
        sa.ForeignKeyConstraint(
            ["alerta_id"],
            ["alerta.id"],
            name=op.f("fk_trecho_alerta_alerta_id_alerta"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["classificacao_id"],
            ["classificacao.id"],
            name=op.f("fk_trecho_alerta_classificacao_id_classificacao"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trecho_alerta")),
        sa.UniqueConstraint(
            "alerta_id",
            "alerta_hash",
            "modelo_embedding",
            "dimensoes",
            "posicao",
            name=op.f("uq_trecho_alerta_alerta_id"),
        ),
    )
    op.create_index(op.f("ix_trecho_alerta_alerta_id"), "trecho_alerta", ["alerta_id"])
    op.create_index("ix_trecho_alerta_paises", "trecho_alerta", ["paises"], postgresql_using="gin")
    op.create_table(
        "contagem_chat",
        sa.Column("dia", sa.Date(), nullable=False),
        sa.Column("chave", sa.String(length=40), nullable=False),
        sa.Column("valor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("valor >= 0", name=op.f("ck_contagem_chat_valor_nao_negativo")),
        sa.PrimaryKeyConstraint("dia", "chave", name=op.f("pk_contagem_chat")),
    )


def downgrade() -> None:
    # A extensão fica: outra coisa pode usá-la
    op.drop_table("contagem_chat")
    op.drop_index("ix_trecho_alerta_paises", table_name="trecho_alerta", postgresql_using="gin")
    op.drop_index(op.f("ix_trecho_alerta_alerta_id"), table_name="trecho_alerta")
    op.drop_table("trecho_alerta")
