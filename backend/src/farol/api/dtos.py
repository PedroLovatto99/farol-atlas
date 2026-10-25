"""DTOs (Pydantic) de entrada e saída da API. Nenhuma rota devolve objetos do banco.

Os nomes e a forma seguem specs/001-mapa-alertas-viagem/contracts/openapi.yaml; um teste de
contrato compara o OpenAPI gerado com ele.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from farol.dominio import TipoPosto

__all__ = [
    "AlertaDoPais",
    "Erro",
    "Fonte",
    "FontePostos",
    "Mapa",
    "Nivel",
    "NivelRegional",
    "Pais",
    "PaisSemPosto",
    "PostoNoMapa",
    "PostoNoPainel",
    "Regiao",
    "Saude",
    "TerritorioNoMapa",
    "TipoPosto",
    "TipoTerritorio",
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
