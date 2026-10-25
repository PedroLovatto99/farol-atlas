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
from farol.mapa.painel import TerritorioNaoEncontrado, montar_painel
from farol.mapa.saude import EstadoDeSaude, consultar_saude
from farol.mapa.servico import montar_mapa
from farol.mapa.visoes import (
    AlertaDoPais,
    FonteDeDados,
    FontePostos,
    PaisSemPosto,
    PostoNoMapa,
    PostoNoPainel,
    TerritorioNoMapa,
    VisaoDoMapa,
    VisaoDoPainel,
)

__all__ = [
    "AlertaDoPais",
    "AlertaParaNivel",
    "EstadoDeSaude",
    "FonteDeDados",
    "FontePostos",
    "ItemDoAlerta",
    "NivelDoTerritorio",
    "NivelExibido",
    "NivelRegional",
    "PaisSemPosto",
    "PostoNoMapa",
    "PostoNoPainel",
    "Regiao",
    "RegiaoDoAlerta",
    "TerritorioNaoEncontrado",
    "TerritorioNoMapa",
    "TerritorioParaNivel",
    "VisaoDoMapa",
    "VisaoDoPainel",
    "calcular_niveis",
    "consultar_saude",
    "montar_mapa",
    "montar_painel",
    "titulo_cita",
]
