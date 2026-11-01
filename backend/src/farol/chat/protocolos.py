"""Protocols que o chat usa para falar com o resto do sistema (contracts/ferramentas-do-chat.md).

Todos são síncronos e só leem. Cada um devolve valores imutáveis (dataclasses), nunca objetos do
banco. As implementações ficam em `farol.api`, que reaproveita as mesmas funções do painel, do
mapa e dos vistos; o chat nunca reescreve regra de nível, visto ou posto.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

Vetor = Sequence[float]


# --------------------------------------------------------------------------- valores devolvidos
@dataclass(frozen=True)
class PaisEncontrado:
    codigo: str
    nome: str
    soberano: str | None = None  # código do soberano, se for dependência


@dataclass(frozen=True)
class ResultadoDaResolucao:
    """Países achados no texto e, para nomes ambíguos (Congo, Guiné), os candidatos."""

    encontrados: tuple[PaisEncontrado, ...] = ()
    ambiguos: tuple[tuple[PaisEncontrado, ...], ...] = ()


@dataclass(frozen=True)
class AlertaQueRege:
    id: int
    titulo: str
    data: datetime
    url: str


@dataclass(frozen=True)
class NivelConsultado:
    codigo: str
    nome: str
    nivel: str | None  # None = sem alerta ou não verificado
    regioes: tuple[str, ...] = ()
    so_regional: bool = False
    alerta_que_rege: AlertaQueRege | None = None
    observacao: str | None = None
    atualizado_em: datetime | None = None
    dados_obtidos: bool = True  # False = ainda não há coleta


@dataclass(frozen=True)
class VistoConsultado:
    codigo: str
    nome: str
    categoria: str
    rotulo: str
    aceita_rg: bool
    observacoes: tuple[tuple[str, str | None], ...] = ()  # (texto, tradução automática)
    coletado_em: datetime | None = None
    desatualizado: bool = False
    fonte: str = ""


@dataclass(frozen=True)
class PostoConsultado:
    cidade: str
    tipo: str
    endereco: str | None = None
    contato: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class PostosConsultados:
    codigo: str
    nome: str
    postos: tuple[PostoConsultado, ...] = ()
    posto_responsavel: str | None = None
    sem_posto_indicado: bool = False
    fonte: str = ""
    atualizado_em: datetime | None = None


@dataclass(frozen=True)
class ItemDeLista:
    codigo: str
    nome: str


@dataclass(frozen=True)
class ListaConsultada:
    criterio: str
    paises: tuple[ItemDeLista, ...] = ()  # todos, em ordem alfabética; o corte é do montador
    fonte: str = ""
    atualizado_em: datetime | None = None
    desatualizado: bool = False
    dados_obtidos: bool = True


# --------------------------------------------------------------------------- Protocols
@runtime_checkable
class ResolvedorDePaises(Protocol):
    def resolver(self, texto: str) -> ResultadoDaResolucao: ...


@runtime_checkable
class ConsultaDeNivel(Protocol):
    def consultar(self, codigo: str) -> NivelConsultado: ...


@runtime_checkable
class ConsultaDeVisto(Protocol):
    def consultar(self, codigo: str) -> VistoConsultado | None: ...


@runtime_checkable
class ConsultaDePostos(Protocol):
    def consultar(self, codigo: str) -> PostosConsultados: ...


@runtime_checkable
class ConsultaDeListas(Protocol):
    def por_nivel(self, nivel: str) -> ListaConsultada: ...

    def por_visto(self, situacao: str, so_rg: bool = False) -> ListaConsultada: ...


@runtime_checkable
class Embeddador(Protocol):
    def vetorizar_documentos(self, textos: Sequence[str]) -> list[Vetor]: ...

    def vetorizar_pergunta(self, texto: str) -> Vetor: ...
