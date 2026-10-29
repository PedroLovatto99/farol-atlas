"""Coleta responsável do Portal Consular. Interface pública do módulo."""

from farol.coleta.extratores import (
    AlertaExtraido,
    ErroDeExtracao,
    ItemDaLista,
    ListaDeAlertas,
    extrair_alerta,
    extrair_lista_de_alertas,
)
from farol.coleta.servico_alertas import (
    URL_LISTA_DE_ALERTAS,
    ResultadoDaColeta,
    ServicoDeColetaDeAlertas,
    hash_do_alerta,
)
from farol.coleta.servico_postos import (
    URL_REPARTICOES,
    ResultadoDaColetaDePostos,
    ServicoDeColetaDePostos,
    associar_postos,
)

__all__ = [
    "URL_LISTA_DE_ALERTAS",
    "URL_REPARTICOES",
    "AlertaExtraido",
    "ErroDeExtracao",
    "ItemDaLista",
    "ListaDeAlertas",
    "ResultadoDaColeta",
    "ResultadoDaColetaDePostos",
    "ServicoDeColetaDeAlertas",
    "ServicoDeColetaDePostos",
    "associar_postos",
    "extrair_alerta",
    "extrair_lista_de_alertas",
    "hash_do_alerta",
]
