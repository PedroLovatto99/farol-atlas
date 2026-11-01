"""O que a `api` entrega ao `chat`: as implementações dos Protocols que precisam do `mapa`.

O `chat` não importa o `mapa` nem o `vistos`; quem os conhece é a `api`, que converte o que eles
devolvem nos valores imutáveis do `chat`. Aqui não há regra de negócio nova.
"""

from farol.api.chat.cors import CorsPorRota
from farol.api.chat.fabrica import fabrica_do_pipeline, montar_pipeline
from farol.api.chat.ferramentas import ConsultaDeNivelDoSite, ResolvedorDePaisesDoSite

__all__ = [
    "ConsultaDeNivelDoSite",
    "CorsPorRota",
    "ResolvedorDePaisesDoSite",
    "fabrica_do_pipeline",
    "montar_pipeline",
]
