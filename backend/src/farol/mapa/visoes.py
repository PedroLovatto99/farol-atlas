"""Visões imutáveis que o serviço do mapa devolve. A API as converte em DTOs; nenhum objeto do
banco sai do módulo."""

from dataclasses import dataclass
from datetime import datetime

from farol.dominio import TipoPosto, TipoTerritorio
from farol.mapa.nivel import NivelExibido, Regiao


@dataclass(frozen=True)
class TerritorioNoMapa:
    codigo: str
    nome: str
    rotulo_busca: str
    termos_busca: tuple[str, ...]
    tipo: TipoTerritorio
    soberano: str | None
    bandeira: str | None
    identidade_do_soberano: bool
    nivel: NivelExibido
    regioes: tuple[Regiao, ...]  # só as regiões com destaque (FR-004)
    observacao: str | None


@dataclass(frozen=True)
class PostoNoMapa:
    id: int
    territorio: str
    tipo: TipoPosto
    cidade: str
    latitude: float
    longitude: float
    grupo: str  # postos na mesma coordenada dividem o ícone (FR-018d)


@dataclass(frozen=True)
class PaisSemPosto:
    territorio: str
    latitude: float
    longitude: float
    posto_responsavel_id: int | None  # None = sem posto indicado (Líbia)


@dataclass(frozen=True)
class VisaoDoMapa:
    dados_obtidos: bool  # houve ao menos uma coleta completa
    atualizado_em: datetime | None  # fim da última coleta completa
    desatualizado: bool  # a última coleta completa tem mais de 3 dias
    territorios: tuple[TerritorioNoMapa, ...]
    postos: tuple[PostoNoMapa, ...]
    paises_sem_posto: tuple[PaisSemPosto, ...]
