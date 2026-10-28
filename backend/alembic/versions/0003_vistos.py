"""requisitos de visto para brasileiros (feature 002): quatro tabelas novas

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28 13:24:31.209543

A 0003 só acrescenta: nenhuma tabela da 001 muda, e o downgrade remove apenas as quatro.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coleta_vistos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resultado",
            sa.Enum(
                "valida",
                "rejeitada",
                "adiada",
                "falhou",
                "bloqueada",
                name="resultado_da_coleta_de_vistos",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("linhas_lidas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("paises_reconhecidos", sa.Integer(), nullable=True),
        sa.Column("ultima_edicao_fonte", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revisao_fonte", sa.BigInteger(), nullable=True),
        sa.Column("adiamentos_seguidos", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("falhas_seguidas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("aplicadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("retidas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("html_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "resultado = 'valida' OR (motivo IS NOT NULL AND btrim(motivo) <> '')",
            name=op.f("ck_coleta_vistos_motivo_exigido_se_nao_valida"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coleta_vistos")),
    )
    op.create_index(
        op.f("ix_coleta_vistos_iniciada_em"), "coleta_vistos", ["iniciada_em"], unique=False
    )
    op.create_table(
        "item_para_revisao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "nome",
                "rotulo",
                "regra",
                name="tipo_de_item_para_revisao",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("contexto", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("primeira_vez_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultima_vez_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "pendente",
                "resolvido",
                "ignorado",
                name="estado_do_item",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("motivo_ignorar", sa.Text(), nullable=True),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado <> 'ignorado' OR (tipo = 'nome' "
            "AND motivo_ignorar IS NOT NULL AND btrim(motivo_ignorar) <> '')",
            name=op.f("ck_item_para_revisao_ignorar_so_nome_com_motivo"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_para_revisao")),
        sa.UniqueConstraint("tipo", "valor", name=op.f("uq_item_para_revisao_tipo")),
    )
    op.create_table(
        "mudanca_retida",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("territorio_codigo", sa.String(length=8), nullable=False),
        sa.Column("coleta_id", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "pendente",
                "confirmada",
                "rejeitada",
                "revertida",
                "superada",
                name="estado_da_retencao",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("hash_fonte_lido", sa.String(length=64), nullable=False),
        sa.Column("candidato", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "categoria_exibida",
            sa.Enum(
                "isento",
                "visto_na_chegada",
                "autorizacao_eletronica",
                "visto_exigido",
                "outra_situacao",
                name="categoria_exibida_retida",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "categoria_lida",
            sa.Enum(
                "isento",
                "visto_na_chegada",
                "autorizacao_eletronica",
                "visto_exigido",
                "outra_situacao",
                name="categoria_lida_retida",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "aceita_rg_exibido", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("aceita_rg_lido", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolvida_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["coleta_id"],
            ["coleta_vistos.id"],
            name=op.f("fk_mudanca_retida_coleta_id_coleta_vistos"),
        ),
        sa.ForeignKeyConstraint(
            ["territorio_codigo"],
            ["territorio.codigo"],
            name=op.f("fk_mudanca_retida_territorio_codigo_territorio"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mudanca_retida")),
    )
    op.create_index(
        op.f("ix_mudanca_retida_territorio_codigo"),
        "mudanca_retida",
        ["territorio_codigo"],
        unique=False,
    )
    op.create_index(
        "uq_mudanca_retida_aberta_por_territorio",
        "mudanca_retida",
        ["territorio_codigo", "estado"],
        unique=True,
        postgresql_where=sa.text("estado IN ('pendente', 'rejeitada')"),
    )
    op.create_table(
        "requisito_visto",
        sa.Column("territorio_codigo", sa.String(length=8), nullable=False),
        sa.Column(
            "categoria",
            sa.Enum(
                "isento",
                "visto_na_chegada",
                "autorizacao_eletronica",
                "visto_exigido",
                "outra_situacao",
                name="categoria_de_visto",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column(
            "motivo_outra",
            sa.Enum(
                "rotulo_conhecido",
                "rotulo_desconhecido",
                name="motivo_outra_situacao",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column("rotulo_original", sa.Text(), nullable=False),
        sa.Column("linhas_fonte", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hash_fonte", sa.String(length=64), nullable=False),
        sa.Column("aceita_rg", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "varia_conforme_motivo", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "permanencia_tipo",
            sa.String(length=40),
            server_default=sa.text("'nenhuma'"),
            nullable=False,
        ),
        sa.Column("permanencia_texto", sa.Text(), nullable=True),
        sa.Column(
            "observacoes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("lido_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coleta_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(categoria = 'outra_situacao') = (motivo_outra IS NOT NULL)",
            name=op.f("ck_requisito_visto_motivo_outra_so_em_outra_situacao"),
        ),
        sa.CheckConstraint(
            "(permanencia_tipo IN ('padronizada', 'original') "
            "AND permanencia_texto IS NOT NULL AND btrim(permanencia_texto) <> '') "
            "OR (permanencia_tipo NOT IN ('padronizada', 'original') "
            "AND permanencia_texto IS NULL)",
            name=op.f("ck_requisito_visto_permanencia_texto_conforme_o_tipo"),
        ),
        sa.CheckConstraint(
            "permanencia_tipo IN "
            "('nenhuma', 'padronizada', 'original', 'prazos_divergentes', 'varia_conforme_motivo')",
            name=op.f("ck_requisito_visto_permanencia_tipo_conhecido"),
        ),
        sa.ForeignKeyConstraint(
            ["coleta_id"],
            ["coleta_vistos.id"],
            name=op.f("fk_requisito_visto_coleta_id_coleta_vistos"),
        ),
        sa.ForeignKeyConstraint(
            ["territorio_codigo"],
            ["territorio.codigo"],
            name=op.f("fk_requisito_visto_territorio_codigo_territorio"),
        ),
        sa.PrimaryKeyConstraint("territorio_codigo", name=op.f("pk_requisito_visto")),
    )


def downgrade() -> None:
    op.drop_table("requisito_visto")
    op.drop_index(
        "uq_mudanca_retida_aberta_por_territorio",
        table_name="mudanca_retida",
        postgresql_where=sa.text("estado IN ('pendente', 'rejeitada')"),
    )
    op.drop_index(op.f("ix_mudanca_retida_territorio_codigo"), table_name="mudanca_retida")
    op.drop_table("mudanca_retida")
    op.drop_table("item_para_revisao")
    op.drop_index(op.f("ix_coleta_vistos_iniciada_em"), table_name="coleta_vistos")
    op.drop_table("coleta_vistos")
