"""O que o chat recebe e devolve, sem importar `mapa` nem `vistos` (research D1, D2).

As visões lidas são `Protocol`s só com os atributos que o chat usa, como `@property` (só leitura):
as dataclasses do `mapa` e do `vistos` as satisfazem sem conversão (os `StrEnum` passam por `str` e
as tuplas por `Sequence`), e o mypy aponta qualquer campo que mude. A `api` faz a ligação.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class TerritorioNaoEncontrado(Exception):
    """O código não tem painel (desconhecido ou área neutra)."""


class TipoDeResposta(StrEnum):
    ALERTA = "alerta"
    VISTO = "visto"
    ALERTA_E_VISTO = "alerta_e_visto"
    QUAL_DOS_PAISES = "qual_dos_paises"
    PEDIR_PAIS = "pedir_pais"
    UM_PAIS_POR_VEZ = "um_pais_por_vez"
    BRASIL = "brasil"
    FORA_DO_ASSUNTO = "fora_do_assunto"
    REFORMULAR = "reformular"


@dataclass(frozen=True)
class Trecho:
    texto: str
    url: str | None = None  # só os links que o painel mostra


Paragrafo = tuple[Trecho, ...]


@dataclass(frozen=True)
class Resposta:
    tipo: TipoDeResposta
    codigo: str | None  # só em alerta, visto e alerta_e_visto
    paragrafos: tuple[Paragrafo, ...]


# ----------------------------------------------------------------------------- mapa
class TerritorioLido(Protocol):
    @property
    def codigo(self) -> str: ...
    @property
    def nome(self) -> str: ...
    @property
    def rotulo_busca(self) -> str: ...
    @property
    def termos_busca(self) -> Sequence[str]: ...
    @property
    def identidade_do_soberano(self) -> bool: ...


class MapaLido(Protocol):
    @property
    def dados_obtidos(self) -> bool: ...
    @property
    def atualizado_em(self) -> datetime | None: ...
    @property
    def desatualizado(self) -> bool: ...
    @property
    def territorios(self) -> Sequence[TerritorioLido]: ...


# ----------------------------------------------------------------------------- painel
class RegiaoLida(Protocol):
    @property
    def nome(self) -> str: ...
    @property
    def nivel(self) -> str: ...


class AlertaLido(Protocol):
    @property
    def titulo(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def publicado_em(self) -> datetime: ...
    @property
    def modificado_em(self) -> datetime | None: ...
    @property
    def define_nivel(self) -> bool: ...
    @property
    def pendente(self) -> bool: ...


class PainelLido(Protocol):
    @property
    def codigo(self) -> str: ...
    @property
    def nome(self) -> str: ...
    @property
    def nivel(self) -> str: ...
    @property
    def regioes(self) -> Sequence[RegiaoLida]: ...
    @property
    def regiao_unica_do_alerta(self) -> bool: ...
    @property
    def observacao(self) -> str | None: ...
    @property
    def alertas(self) -> Sequence[AlertaLido]: ...


# ----------------------------------------------------------------------------- visto
class FonteLida(Protocol):
    @property
    def nome(self) -> str: ...
    @property
    def url(self) -> str: ...
    @property
    def licenca(self) -> str | None: ...


class PermanenciaLida(Protocol):
    @property
    def tipo(self) -> str: ...
    @property
    def texto(self) -> str | None: ...


class ObservacaoLida(Protocol):
    @property
    def texto_original(self) -> str: ...
    @property
    def traducao(self) -> str | None: ...


class VistoLido(Protocol):
    @property
    def situacao(self) -> str: ...
    @property
    def rotulo_original(self) -> str | None: ...
    @property
    def aceita_rg(self) -> bool: ...
    @property
    def varia_conforme_motivo(self) -> bool: ...
    @property
    def permanencia(self) -> PermanenciaLida | None: ...
    @property
    def observacoes(self) -> Sequence[ObservacaoLida]: ...
    @property
    def origem(self) -> str | None: ...
    @property
    def soberano_nome(self) -> str | None: ...
    @property
    def territorio_nome(self) -> str | None: ...
    @property
    def dado_de(self) -> datetime | None: ...
    @property
    def desatualizado(self) -> bool: ...
    @property
    def fonte(self) -> FonteLida: ...


class PainelComVistoLido(Protocol):
    @property
    def painel(self) -> PainelLido: ...
    @property
    def visto(self) -> VistoLido | None: ...


# ----------------------------------------------------------------------------- portas
class FonteDoPainel(Protocol):
    """Os mesmos dados do painel (paridade por construção, SC-001)."""

    def mapa(self) -> MapaLido: ...

    def painel(self, codigo: str) -> PainelComVistoLido:
        """Levanta `TerritorioNaoEncontrado` se o código não tem painel."""
        ...


@dataclass(frozen=True)
class PalpiteDoModelo:
    """O que o modelo devolve, ainda sem validar contra a lista de territórios."""

    codigos: tuple[str, ...]
    assunto: str


class ModeloDeEntendimento(Protocol):
    def entender(self, pergunta: str, territorios: Mapping[str, str]) -> PalpiteDoModelo | None:
        """País e assunto da pergunta; `territorios` é código -> nome. None = não respondeu."""
        ...
