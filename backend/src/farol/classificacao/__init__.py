"""Classificação de alertas por modelo de linguagem. Interface pública do módulo."""

from farol.classificacao.cadeia import ClassificadorDeAlertas, EntradaDoAlerta, criar_modelo
from farol.classificacao.esquema import (
    Classificacao,
    RegiaoClassificada,
    RespostaInvalida,
    TerritorioClassificado,
    validar_resposta,
)
from farol.classificacao.servico import (
    Classificador,
    ResultadoDaClassificacao,
    ServicoDeClassificacao,
)

__all__ = [
    "Classificacao",
    "Classificador",
    "ClassificadorDeAlertas",
    "EntradaDoAlerta",
    "RegiaoClassificada",
    "RespostaInvalida",
    "ResultadoDaClassificacao",
    "ServicoDeClassificacao",
    "TerritorioClassificado",
    "criar_modelo",
    "validar_resposta",
]
