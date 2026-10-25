"""Visões imutáveis que o serviço do mapa devolve. A API as converte em DTOs; nenhum objeto do
banco sai do módulo."""

from dataclasses import dataclass
from datetime import date, datetime

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


# ----------------------------------------------------------------------------- painel
@dataclass(frozen=True)
class AlertaDoPais:
    titulo: str
    url: str
    publicado_em: datetime
    modificado_em: datetime | None
    define_nivel: bool  # é o alerta mais recente, que rege o nível (FR-010)
    situacao_normalizada: bool
    pendente: bool  # ainda sem classificação válida (FR-008)


@dataclass(frozen=True)
class PostoNoPainel:
    id: int
    tipo: TipoPosto
    cidade: str
    pais: str  # nome do país do posto (útil para o posto responsável)
    grupo: str
    endereco: str | None
    telefone_plantao: str | None
    contato_coletado_em: datetime | None
    contato_fonte_url: str | None


@dataclass(frozen=True)
class FonteDeDados:
    nome: str
    url: str
    licenca: str | None


@dataclass(frozen=True)
class FontePostos:
    conferido_em: date
    fontes: tuple[FonteDeDados, ...]


@dataclass(frozen=True)
class VisaoDoPainel:
    codigo: str
    nome: str
    tipo: TipoTerritorio
    soberano: str | None
    bandeira: str | None
    identidade_do_soberano: bool
    nivel: NivelExibido
    regioes: tuple[Regiao, ...]
    regiao_unica_do_alerta: bool  # o alerta que rege só tem nível regional (FR-007)
    observacao: str | None
    observacao_no_topo: bool  # Kosovo e Malvinas (FR-030, FR-034)
    eh_brasil: bool
    alertas: tuple[AlertaDoPais, ...]
    postos: tuple[PostoNoPainel, ...]
    posto_responsavel: PostoNoPainel | None
    sem_posto_indicado: bool
    fonte_postos: FontePostos | None
