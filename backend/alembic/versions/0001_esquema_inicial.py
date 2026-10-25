"""esquema inicial

Revision ID: 0001
Revises:
Create Date: 2026-10-23 17:12:05.932197
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execucao_coleta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "alertas",
                "postos",
                name="tipo_execucao",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("iniciada_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paginas_esperadas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("paginas_lidas", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "lista_lida_inteira", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("completa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("motivo_interrupcao", sa.Text(), nullable=True),
        sa.Column("postos_com_endereco", sa.Integer(), nullable=True),
        sa.Column("postos_com_telefone", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_execucao_coleta")),
    )
    op.create_table(
        "fonte_dados",
        sa.Column("chave", sa.String(length=40), nullable=False),
        sa.Column("fontes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("conferido_em", sa.Date(), nullable=False),
        sa.Column("carregado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("chave", name=op.f("pk_fonte_dados")),
    )
    op.create_table(
        "territorio",
        sa.Column("codigo", sa.String(length=8), nullable=False),
        sa.Column("nome_pt", sa.Text(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "pais",
                "dependencia",
                "neutro",
                name="tipo_territorio",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("soberano_codigo", sa.String(length=8), nullable=True),
        sa.Column(
            "na_lista_itamaraty", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("codigo_bandeira", sa.String(length=8), nullable=True),
        sa.Column(
            "identidade_do_soberano", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("rotulo_busca", sa.Text(), nullable=True),
        sa.Column(
            "termos_busca",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("posto_responsavel_id", sa.Integer(), nullable=True),
        sa.Column(
            "sem_posto_indicado", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("icone_latitude", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("icone_longitude", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.CheckConstraint(
            "tipo <> 'dependencia' OR soberano_codigo IS NOT NULL",
            name=op.f("ck_territorio_dependencia_exige_soberano"),
        ),
        sa.ForeignKeyConstraint(
            ["soberano_codigo"],
            ["territorio.codigo"],
            name=op.f("fk_territorio_soberano_codigo_territorio"),
        ),
        sa.PrimaryKeyConstraint("codigo", name=op.f("pk_territorio")),
    )
    op.create_table(
        "alerta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("titulo", sa.Text(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=True),
        sa.Column("html_corpo", sa.Text(), nullable=True),
        sa.Column("categoria", sa.Text(), nullable=True),
        sa.Column("publicado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modificado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("primeira_coleta_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultima_coleta_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pagina_lida", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("confirmado_execucao_id", sa.Integer(), nullable=True),
        sa.Column("confirmado_hash", sa.String(length=64), nullable=True),
        sa.Column("confirmado_titulo", sa.Text(), nullable=True),
        sa.Column("confirmado_data_ref", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["confirmado_execucao_id"],
            ["execucao_coleta.id"],
            name=op.f("fk_alerta_confirmado_execucao_id_execucao_coleta"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerta")),
        sa.UniqueConstraint("url", name=op.f("uq_alerta_url")),
    )
    op.create_table(
        "posto",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("territorio_codigo", sa.String(length=8), nullable=False),
        sa.Column("cidade", sa.Text(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "Embaixada",
                "Consulado-Geral",
                "Consulado",
                "Vice-Consulado",
                "Escritório de Representação",
                "Escritório Comercial",
                name="tipo_posto",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("latitude", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=8, scale=5), nullable=False),
        sa.Column("na_lista_oficial", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("observacao_origem", sa.Text(), nullable=True),
        sa.Column("url_gov_br", sa.Text(), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("telefone_plantao", sa.Text(), nullable=True),
        sa.Column("contato_coletado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contato_fonte_url", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "(endereco IS NULL AND telefone_plantao IS NULL) "
            "OR (contato_coletado_em IS NOT NULL AND contato_fonte_url IS NOT NULL)",
            name=op.f("ck_posto_contato_exige_fonte_e_data"),
        ),
        sa.ForeignKeyConstraint(
            ["territorio_codigo"],
            ["territorio.codigo"],
            name=op.f("fk_posto_territorio_codigo_territorio"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posto")),
    )
    op.create_index(
        op.f("ix_posto_territorio_codigo"), "posto", ["territorio_codigo"], unique=False
    )
    op.create_table(
        "classificacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alerta_id", sa.Integer(), nullable=False),
        sa.Column("alerta_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ok",
                "falhou",
                name="status_classificacao",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("e_alerta_de_viagem", sa.Boolean(), nullable=True),
        sa.Column("modelo", sa.Text(), nullable=False),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("classificado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["alerta_id"], ["alerta.id"], name=op.f("fk_classificacao_alerta_id_alerta")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classificacao")),
        sa.UniqueConstraint("alerta_id", "alerta_hash", name=op.f("uq_classificacao_alerta_id")),
    )
    op.create_index(
        op.f("ix_classificacao_alerta_id"), "classificacao", ["alerta_id"], unique=False
    )
    op.create_table(
        "nivel_territorio",
        sa.Column("classificacao_id", sa.Integer(), nullable=False),
        sa.Column("territorio_codigo", sa.String(length=8), nullable=False),
        sa.Column(
            "nivel_pais",
            sa.Enum(
                "evitar",
                "nao_viajar",
                "normalizada",
                name="nivel_alerta",
                native_enum=False,
                create_constraint=True,
                length=40,
            ),
            nullable=True,
        ),
        sa.Column(
            "regioes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["classificacao_id"],
            ["classificacao.id"],
            name=op.f("fk_nivel_territorio_classificacao_id_classificacao"),
        ),
        sa.ForeignKeyConstraint(
            ["territorio_codigo"],
            ["territorio.codigo"],
            name=op.f("fk_nivel_territorio_territorio_codigo_territorio"),
        ),
        sa.PrimaryKeyConstraint(
            "classificacao_id", "territorio_codigo", name=op.f("pk_nivel_territorio")
        ),
    )

    # Chave circular (territorio <-> posto): criada depois das duas tabelas
    op.create_foreign_key(
        op.f("fk_territorio_posto_responsavel_id_posto"),
        "territorio",
        "posto",
        ["posto_responsavel_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_territorio_posto_responsavel_id_posto"), "territorio", type_="foreignkey"
    )
    op.drop_table("nivel_territorio")
    op.drop_index(op.f("ix_classificacao_alerta_id"), table_name="classificacao")
    op.drop_table("classificacao")
    op.drop_index(op.f("ix_posto_territorio_codigo"), table_name="posto")
    op.drop_table("posto")
    op.drop_table("alerta")
    op.drop_table("territorio")
    op.drop_table("fonte_dados")
    op.drop_table("execucao_coleta")
