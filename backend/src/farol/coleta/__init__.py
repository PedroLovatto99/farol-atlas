"""Coleta responsável do Portal Consular. Interface pública do módulo."""

from farol.coleta.cliente_educado import ClienteEducado, Pagina
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
    Baixador,
    ResultadoDaColeta,
    ServicoDeColetaDeAlertas,
    hash_do_alerta,
)

__all__ = [
    "URL_LISTA_DE_ALERTAS",
    "AlertaExtraido",
    "Baixador",
    "ClienteEducado",
    "ErroDeExtracao",
    "ItemDaLista",
    "ListaDeAlertas",
    "Pagina",
    "ResultadoDaColeta",
    "ServicoDeColetaDeAlertas",
    "extrair_alerta",
    "extrair_lista_de_alertas",
    "hash_do_alerta",
]
