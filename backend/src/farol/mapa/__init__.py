"""Casos de uso de leitura do mapa: níveis, painel e saúde. Interface pública do módulo."""

from farol.mapa.nivel import (
    AlertaParaNivel,
    ItemDoAlerta,
    NivelDoTerritorio,
    NivelExibido,
    NivelRegional,
    Regiao,
    RegiaoDoAlerta,
    TerritorioParaNivel,
    calcular_niveis,
    titulo_cita,
)
from farol.mapa.saude import EstadoDeSaude, consultar_saude
from farol.mapa.servico import montar_mapa
from farol.mapa.visoes import (
    PaisSemPosto,
    PostoNoMapa,
    TerritorioNoMapa,
    VisaoDoMapa,
)

__all__ = [
    "AlertaParaNivel",
    "EstadoDeSaude",
    "ItemDoAlerta",
    "NivelDoTerritorio",
    "NivelExibido",
    "NivelRegional",
    "PaisSemPosto",
    "PostoNoMapa",
    "Regiao",
    "RegiaoDoAlerta",
    "TerritorioNoMapa",
    "TerritorioParaNivel",
    "VisaoDoMapa",
    "calcular_niveis",
    "consultar_saude",
    "montar_mapa",
    "titulo_cita",
]
