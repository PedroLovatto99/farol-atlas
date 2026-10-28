"""Visões imutáveis do visto, devolvidas à `api`: o que a leitura resolve, sem objetos do banco."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from farol.dominio import MotivoOutraSituacao
from farol.vistos.permanencia import TipoDePermanencia


class SituacaoDeVisto(StrEnum):
    """Situação de visto de um território com painel (FR-002, FR-011)."""

    ISENTO = "isento"
    VISTO_NA_CHEGADA = "visto_na_chegada"
    AUTORIZACAO_ELETRONICA = "autorizacao_eletronica"
    VISTO_EXIGIDO = "visto_exigido"
    OUTRA_SITUACAO = "outra_situacao"
    SEM_INFORMACAO = "sem_informacao"


class SituacaoNoGlobo(StrEnum):
    """A situação do painel mais `nao_se_aplica`, só para o Brasil (FR-023)."""

    ISENTO = "isento"
    VISTO_NA_CHEGADA = "visto_na_chegada"
    AUTORIZACAO_ELETRONICA = "autorizacao_eletronica"
    VISTO_EXIGIDO = "visto_exigido"
    OUTRA_SITUACAO = "outra_situacao"
    SEM_INFORMACAO = "sem_informacao"
    NAO_SE_APLICA = "nao_se_aplica"


class OrigemDoVisto(StrEnum):
    """A entrada é a do próprio território (ou da identidade dele) ou a do soberano (FR-013)."""

    PROPRIO = "proprio"
    SOBERANO = "soberano"


@dataclass(frozen=True)
class FonteDosVistos:
    nome: str
    url: str
    licenca: str | None


@dataclass(frozen=True)
class PermanenciaDoVisto:
    tipo: TipoDePermanencia
    texto: str | None  # só em `padronizada` (português) e `original` (inglês)


@dataclass(frozen=True)
class ObservacaoDoVisto:
    texto_original: str  # texto puro, em inglês
    traducao: str | None  # nulo se ainda não foi traduzida


@dataclass(frozen=True)
class VisaoDoVisto:
    """A seção "Visto" do painel de um território."""

    situacao: SituacaoDeVisto
    motivo_outra_situacao: MotivoOutraSituacao | None
    rotulo_original: str | None
    aceita_rg: bool
    varia_conforme_motivo: bool
    permanencia: PermanenciaDoVisto | None
    observacoes: tuple[ObservacaoDoVisto, ...]
    origem: OrigemDoVisto | None
    soberano_nome: str | None  # preenchido só quando `origem` é `soberano`
    # Nome do território a que o visto se refere quando o painel tem a identidade de outro
    # (Kosovo, Ilhas Malvinas); nulo nos demais. A seção se intitula "Visto: <nome>".
    territorio_nome: str | None
    dado_de: datetime | None  # a data do dado mostrado para este território (FR-008)
    desatualizado: bool  # `dado_de` tem mais de 14 dias (FR-015)
    fonte: FonteDosVistos


@dataclass(frozen=True)
class TerritorioComVisto:
    codigo: str
    situacao: SituacaoNoGlobo
    aceita_rg: bool


@dataclass(frozen=True)
class VisaoDosVistos:
    """O que o globo precisa no modo "Vistos" (`GET /vistos`)."""

    dados_obtidos: bool
    coletado_em: datetime | None  # fim da última coleta válida
    desatualizado: bool  # a última coleta válida tem mais de 14 dias (FR-029a)
    fonte: FonteDosVistos
    territorios: tuple[TerritorioComVisto, ...]
