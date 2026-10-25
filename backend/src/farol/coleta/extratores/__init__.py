"""Extratores das páginas do Portal Consular."""

from farol.coleta.extratores.alerta import AlertaExtraido, ErroDeExtracao, extrair_alerta
from farol.coleta.extratores.lista_alertas import (
    ItemDaLista,
    ListaDeAlertas,
    data_da_lista,
    extrair_lista_de_alertas,
)
from farol.coleta.extratores.posto import (
    ContatoExtraido,
    extrair_contato,
    links_de_contato,
    sem_rotulos_de_pagina,
)
from farol.coleta.extratores.reparticoes import (
    LinhaDeReparticao,
    LinkDePosto,
    extrair_reparticoes,
)

__all__ = [
    "AlertaExtraido",
    "ContatoExtraido",
    "ErroDeExtracao",
    "ItemDaLista",
    "LinhaDeReparticao",
    "LinkDePosto",
    "ListaDeAlertas",
    "data_da_lista",
    "extrair_alerta",
    "extrair_contato",
    "extrair_lista_de_alertas",
    "extrair_reparticoes",
    "links_de_contato",
    "sem_rotulos_de_pagina",
]
