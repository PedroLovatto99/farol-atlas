"""Junta o painel (do `mapa`) e o visto (do `vistos`) numa só visão de `GET /paises/{codigo}`.

A `api` é a única que conhece os dois módulos, que não se importam entre si. Aqui não há regra de
negócio: só a chamada de cada um e a junção do que devolvem.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from farol.infra import Relogio
from farol.mapa import VisaoDoPainel, montar_painel
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
