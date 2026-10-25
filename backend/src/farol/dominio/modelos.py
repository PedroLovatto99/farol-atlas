"""Modelos ORM (SQLAlchemy 2), conforme specs/001-mapa-alertas-viagem/data-model.md.

Só os repositórios usam estes modelos para falar com o banco.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from farol.dominio.enums import (
    NivelAlerta,
    StatusClassificacao,
    TipoExecucao,
    TipoPosto,
    TipoTerritorio,
)

# Nomes previsíveis para restrições: o Alembic precisa deles para migrar com segurança
CONVENCAO_DE_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_DE_NOMES)


def _enum(tipo: type[StrEnum], nome: str) -> Enum:
    """Enum gravado como texto (com CHECK), o que facilita migrar valores depois."""
    return Enum(
        tipo,
        name=nome,
        native_enum=False,
        create_constraint=True,
        length=40,
        values_callable=lambda membros: [m.value for m in membros],
    )


class Territorio(Base):
    """Lugar selecionável ou desenhável no mapa: país, dependência ou área neutra."""

    __tablename__ = "territorio"
    __table_args__ = (
        CheckConstraint(
            "tipo <> 'dependencia' OR soberano_codigo IS NOT NULL",
            name="dependencia_exige_soberano",
        ),
    )

    codigo: Mapped[str] = mapped_column(String(8), primary_key=True)
    nome_pt: Mapped[str] = mapped_column(Text)
    tipo: Mapped[TipoTerritorio] = mapped_column(_enum(TipoTerritorio, "tipo_territorio"))
    soberano_codigo: Mapped[str | None] = mapped_column(ForeignKey("territorio.codigo"))
    na_lista_itamaraty: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    codigo_bandeira: Mapped[str | None] = mapped_column(String(8))
    identidade_do_soberano: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )
    # As regiões nomeadas de um alerta cobrem o território inteiro (ex.: Palestina = Gaza e
    # Cisjordânia): sem nível do país, a cor é a da região menos grave (observacoes.yaml)
    regioes_cobrem_o_pais: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    rotulo_busca: Mapped[str | None] = mapped_column(Text)
    termos_busca: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default=text("'{}'")
    )
    observacao: Mapped[str | None] = mapped_column(Text)
    posto_responsavel_id: Mapped[int | None] = mapped_column(
        ForeignKey("posto.id", use_alter=True, name="fk_territorio_posto_responsavel_id_posto")
    )
    sem_posto_indicado: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    icone_latitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))
    icone_longitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 5))


class Posto(Base):
    """Embaixada, consulado ou escritório do Brasil."""

    __tablename__ = "posto"
    __table_args__ = (
        # Princípio V: todo endereço ou telefone exibido tem fonte e data da coleta
        CheckConstraint(
            "(endereco IS NULL AND telefone_plantao IS NULL) "
            "OR (contato_coletado_em IS NOT NULL AND contato_fonte_url IS NOT NULL)",
            name="contato_exige_fonte_e_data",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    territorio_codigo: Mapped[str] = mapped_column(ForeignKey("territorio.codigo"), index=True)
    cidade: Mapped[str] = mapped_column(Text)
    tipo: Mapped[TipoPosto] = mapped_column(_enum(TipoPosto, "tipo_posto"))
    latitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    longitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    na_lista_oficial: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    observacao_origem: Mapped[str | None] = mapped_column(Text)
    url_gov_br: Mapped[str | None] = mapped_column(Text)
    endereco: Mapped[str | None] = mapped_column(Text)
    telefone_plantao: Mapped[str | None] = mapped_column(Text)
    contato_coletado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    contato_fonte_url: Mapped[str | None] = mapped_column(Text)


class ExecucaoColeta(Base):
    """Uma rodada de coleta (de alertas ou de postos), completa ou não."""

    __tablename__ = "execucao_coleta"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoExecucao] = mapped_column(_enum(TipoExecucao, "tipo_execucao"))
    iniciada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paginas_esperadas: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    paginas_lidas: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    lista_lida_inteira: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    completa: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    motivo_interrupcao: Mapped[str | None] = mapped_column(Text)
    postos_com_endereco: Mapped[int | None]
    postos_com_telefone: Mapped[int | None]


class Alerta(Base):
    """Item da lista de alertas do Portal Consular (histórico)."""

    __tablename__ = "alerta"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    titulo: Mapped[str] = mapped_column(Text)
    # Nulos enquanto a página do alerta não foi lida (pagina_lida = false)
    texto: Mapped[str | None] = mapped_column(Text)
    html_corpo: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str | None] = mapped_column(Text)
    publicado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    modificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hash: Mapped[str | None] = mapped_column(String(64))
    primeira_coleta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultima_coleta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pagina_lida: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    # O que uma execução COMPLETA confirmou; só isto vale para o nível (FR-040, SC-008)
    confirmado_execucao_id: Mapped[int | None] = mapped_column(ForeignKey("execucao_coleta.id"))
    confirmado_hash: Mapped[str | None] = mapped_column(String(64))
    confirmado_titulo: Mapped[str | None] = mapped_column(Text)
    confirmado_data_ref: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    classificacoes: Mapped[list["Classificacao"]] = relationship(
        back_populates="alerta", order_by="Classificacao.id"
    )

    def classificacao_vigente(self) -> "Classificacao | None":
        """Classificação `ok` do conteúdo confirmado; sem ela, o alerta está pendente."""
        if self.confirmado_hash is None:
            return None
        for classificacao in self.classificacoes:
            if (
                classificacao.alerta_hash == self.confirmado_hash
                and classificacao.status is StatusClassificacao.OK
            ):
                return classificacao
        return None


class Classificacao(Base):
    """Resultado de classificar o conteúdo (hash) de um alerta."""

    __tablename__ = "classificacao"
    __table_args__ = (UniqueConstraint("alerta_id", "alerta_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alerta_id: Mapped[int] = mapped_column(ForeignKey("alerta.id"), index=True)
    alerta_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[StatusClassificacao] = mapped_column(
        _enum(StatusClassificacao, "status_classificacao")
    )
    e_alerta_de_viagem: Mapped[bool | None]
    modelo: Mapped[str] = mapped_column(Text)
    erro: Mapped[str | None] = mapped_column(Text)
    classificado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    alerta: Mapped[Alerta] = relationship(back_populates="classificacoes")
    niveis: Mapped[list["NivelTerritorio"]] = relationship(
        back_populates="classificacao",
        order_by="NivelTerritorio.territorio_codigo",
        cascade="all, delete-orphan",
    )


class NivelTerritorio(Base):
    """Nível que uma classificação atribui a um território (país ou dependência)."""

    __tablename__ = "nivel_territorio"

    classificacao_id: Mapped[int] = mapped_column(ForeignKey("classificacao.id"), primary_key=True)
    territorio_codigo: Mapped[str] = mapped_column(
        ForeignKey("territorio.codigo"), primary_key=True
    )
    # Nulo = o alerta só tem nível regional para este território
    nivel_pais: Mapped[NivelAlerta | None] = mapped_column(_enum(NivelAlerta, "nivel_alerta"))
    regioes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    classificacao: Mapped[Classificacao] = relationship(back_populates="niveis")


class FonteDados(Base):
    """Fonte e data dos dados do seed (hoje, os postos), para a atribuição no painel."""

    __tablename__ = "fonte_dados"

    chave: Mapped[str] = mapped_column(String(40), primary_key=True)
    fontes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    conferido_em: Mapped[date] = mapped_column(Date)
    carregado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
