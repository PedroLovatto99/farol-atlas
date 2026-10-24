"""Extratores das páginas do Portal Consular."""

from farol.coleta.extratores.alerta import AlertaExtraido, ErroDeExtracao, extrair_alerta
from farol.coleta.extratores.lista_alertas import (
    ItemDaLista,
    ListaDeAlertas,
    data_da_lista,
    extrair_lista_de_alertas,
)

__all__ = [
    "AlertaExtraido",
    "ErroDeExtracao",
    "ItemDaLista",
    "ListaDeAlertas",
    "data_da_lista",
    "extrair_alerta",
    "extrair_lista_de_alertas",
]
