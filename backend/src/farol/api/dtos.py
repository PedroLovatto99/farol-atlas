"""DTOs (Pydantic) de entrada e saída da API. Nenhuma rota devolve objetos do banco.

Os nomes e a forma seguem specs/002-visto-brasileiros/contracts/openapi.yaml (a API v1.1, que contém
a v1.0 da 001 por inteiro); um teste de contrato compara o OpenAPI gerado com ele.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from farol.dominio import MotivoOutraSituacao, TipoPosto

__all__ = [
    "AlertaDoPais",
    "Erro",
    "Fonte",
    "FontePostos",
    "Mapa",
    "MotivoOutraSituacao",
    "Nivel",
    "NivelRegional",
    "ObservacaoDeVisto",
    "OrigemDoVisto",
    "Pais",
    "PaisSemPosto",
    "Permanencia",
    "PostoNoMapa",
    "PostoNoPainel",
    "Regiao",
    "Saude",
    "SituacaoDeVisto",
    "SituacaoNoGlobo",
    "TerritorioDeVisto",
    "TerritorioNoMapa",
    "TipoDePermanencia",
    "TipoPosto",
    "TipoTerritorio",
    "Visto",
    "VistosDoMapa",
]


class Erro(BaseModel):
    detalhe: str


class Saude(BaseModel):
    banco: Literal["ok", "falha"]
    ultima_coleta_completa_em: datetime | None
    ultima_tentativa_em: datetime | None
    alertas_pendentes: int


# --------------------------------------------------------------------------- /mapa
class Nivel(StrEnum):
    """Nível exibido de um território (FR-001)."""

    SEM_ALERTA = "sem_alerta"
    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"
    NAO_VERIFICADO = "nao_verificado"


class NivelRegional(StrEnum):
    """Nível de uma região dentro de um alerta."""

    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"


class TipoTerritorio(StrEnum):
    PAIS = "pais"
    DEPENDENCIA = "dependencia"


class Regiao(BaseModel):
    nome: str
    nivel: NivelRegional


class TerritorioNoMapa(BaseModel):
    codigo: str
    nome: str
    rotulo_busca: str
    termos_busca: list[str]
    tipo: TipoTerritorio
    soberano: str | None
    bandeira: str | None
    identidade_do_soberano: bool
    nivel: Nivel
    regioes: list[Regiao]
    observacao: str | None


class PostoNoMapa(BaseModel):
    id: int
    territorio: str
    tipo: TipoPosto
    cidade: str
    latitude: float
    longitude: float
    grupo: str


class PaisSemPosto(BaseModel):
    territorio: str
    latitude: float
    longitude: float
    posto_responsavel_id: int | None


class Mapa(BaseModel):
    dados_obtidos: bool
    atualizado_em: datetime | None
    desatualizado: bool
    territorios: list[TerritorioNoMapa]
    postos: list[PostoNoMapa]
    paises_sem_posto: list[PaisSemPosto]


# --------------------------------------------------------------------------- /paises/{codigo}
# Texto que é um endereço absoluto: `str` com `format: uri` no OpenAPI. Não usa `AnyUrl`, que
# reescreveria a URL (o link do gov.br tem de sair exatamente como foi coletado).
Url = Annotated[str, Field(json_schema_extra={"format": "uri"})]


class AlertaDoPais(BaseModel):
    titulo: str
    url: Url
    publicado_em: datetime
    modificado_em: datetime | None
    define_nivel: bool
    situacao_normalizada: bool
    pendente: bool = False


class PostoNoPainel(BaseModel):
    id: int
    tipo: TipoPosto
    cidade: str
    pais: str
    grupo: str
    endereco: str | None
    telefone_plantao: str | None
    contato_coletado_em: datetime | None
    contato_fonte_url: Url | None


class Fonte(BaseModel):
    nome: str
    url: Url
    licenca: str | None = None


class FontePostos(BaseModel):
    conferido_em: date
    fontes: list[Fonte]


# --------------------------------------------------------------------------- visto (feature 002)
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
    """A entrada é a do próprio território ou a do soberano (FR-013)."""

    PROPRIO = "proprio"
    SOBERANO = "soberano"


class TipoDePermanencia(StrEnum):
    """Como a permanência é mostrada (FR-004a, FR-007, FR-007a)."""

    PADRONIZADA = "padronizada"
    ORIGINAL = "original"
    PRAZOS_DIVERGENTES = "prazos_divergentes"
    VARIA_CONFORME_MOTIVO = "varia_conforme_motivo"


class Permanencia(BaseModel):
    tipo: TipoDePermanencia
    texto: str | None


class ObservacaoDeVisto(BaseModel):
    texto_original: str
    traducao: str | None


class Visto(BaseModel):
    situacao: SituacaoDeVisto
    motivo_outra_situacao: MotivoOutraSituacao | None
    rotulo_original: str | None
    aceita_rg: bool
    varia_conforme_motivo: bool
    permanencia: Permanencia | None
    observacoes: list[ObservacaoDeVisto]
    origem: OrigemDoVisto | None
    soberano_nome: str | None
    territorio_nome: str | None
    dado_de: datetime | None
    desatualizado: bool
    fonte: Fonte


class Pais(BaseModel):
    codigo: str
    nome: str
    tipo: TipoTerritorio
    soberano: str | None
    bandeira: str | None
    identidade_do_soberano: bool
    nivel: Nivel
    regioes: list[Regiao]
    regiao_unica_do_alerta: bool = False
    observacao: str | None
    observacao_no_topo: bool
    eh_brasil: bool
    alertas: list[AlertaDoPais]
    postos: list[PostoNoPainel]
    posto_responsavel: PostoNoPainel | None
    sem_posto_indicado: bool
    fonte_postos: FontePostos | None
    visto: Visto | None


# --------------------------------------------------------------------------- /vistos
class TerritorioDeVisto(BaseModel):
    codigo: str
    situacao: SituacaoNoGlobo
    aceita_rg: bool


class VistosDoMapa(BaseModel):
    dados_obtidos: bool
    coletado_em: datetime | None
    desatualizado: bool
    fonte: Fonte
    territorios: list[TerritorioDeVisto]
