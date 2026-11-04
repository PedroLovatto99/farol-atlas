"""Junta o painel (do `mapa`) e o visto (do `vistos`) numa só visão de `GET /paises/{codigo}`, e
entrega os mesmos dados ao `chat`.

A `api` é a única que conhece os dois módulos, que não se importam entre si. Aqui não há regra de
negócio: só a chamada de cada um e a junção do que devolvem.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from farol.chat import TerritorioNaoEncontrado as TerritorioSemPainel
from farol.infra import Relogio
from farol.mapa import (
    TerritorioNaoEncontrado,
    VisaoDoMapa,
    VisaoDoPainel,
    montar_mapa,
    montar_painel,
)
from farol.vistos import VisaoDoVisto, montar_visto_do_pais


@dataclass(frozen=True)
class PainelComVisto:
    painel: VisaoDoPainel
    visto: VisaoDoVisto | None  # nulo só no Brasil (FR-014)


def montar_painel_com_visto(sessao: Session, relogio: Relogio, codigo: str) -> PainelComVisto:
    """O painel do território com a seção de visto. Levanta `TerritorioNaoEncontrado` (do mapa) se
    o código é desconhecido ou de área neutra."""
    painel = montar_painel(sessao, codigo)
    return PainelComVisto(painel, montar_visto_do_pais(sessao, painel.codigo, relogio))


class FonteDoPainelDaApi:
    """Cumpre `farol.chat.FonteDoPainel` com as mesmas funções do painel (SC-001)."""

    def __init__(self, sessao: Session, relogio: Relogio) -> None:
        self._sessao = sessao
        self._relogio = relogio

    def mapa(self) -> VisaoDoMapa:
        mapa = montar_mapa(self._sessao, self._relogio)
        self._sessao.commit()  # devolve a conexão: o modelo vem depois e leva até 5 s
        return mapa

    def painel(self, codigo: str) -> PainelComVisto:
        try:
            return montar_painel_com_visto(self._sessao, self._relogio, codigo)
        except TerritorioNaoEncontrado as erro:
            raise TerritorioSemPainel(codigo) from erro
