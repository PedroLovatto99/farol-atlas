"""DTOs (Pydantic) de entrada e saída da API. Nenhuma rota devolve objetos do banco.

Os nomes e a forma seguem specs/001-mapa-alertas-viagem/contracts/openapi.yaml; um teste de
contrato compara o OpenAPI gerado com ele.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from farol.dominio import TipoPosto

__all__ = [
    "Erro",
    "Mapa",
    "Nivel",
    "NivelRegional",
    "PaisSemPosto",
    "PostoNoMapa",
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
