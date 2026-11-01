"""Protocols do chat (contracts/ferramentas-do-chat.md, seção 2) e os valores imutáveis deles."""

import dataclasses
from typing import Any, Protocol

import pytest

from farol.chat import protocolos
from farol.chat.protocolos import (
    ConsultaDeListas,
    ConsultaDeNivel,
    ConsultaDePostos,
    ConsultaDeVisto,
    Embeddador,
    ListaConsultada,
    NivelConsultado,
    PostosConsultados,
    ResolvedorDePaises,
    ResultadoDaResolucao,
    VistoConsultado,
)

PROTOCOLOS_E_METODOS: list[tuple[type, set[str]]] = [
    (ResolvedorDePaises, {"resolver"}),
    (ConsultaDeNivel, {"consultar"}),
    (ConsultaDeVisto, {"consultar"}),
    (ConsultaDePostos, {"consultar"}),
    (ConsultaDeListas, {"por_nivel", "por_visto"}),
    (Embeddador, {"vetorizar_documentos", "vetorizar_pergunta"}),
]
VALORES = [
    ResultadoDaResolucao,
    NivelConsultado,
    VistoConsultado,
    PostosConsultados,
    ListaConsultada,
]


@pytest.mark.parametrize(("protocolo", "metodos"), PROTOCOLOS_E_METODOS)
def test_e_um_protocol_que_se_pode_conferir_em_tempo_de_execucao(
    protocolo: type, metodos: set[str]
) -> None:
    assert Protocol in protocolo.__mro__
    assert getattr(protocolo, "_is_runtime_protocol", False) is True

    completo: Any = type("Completo", (), {nome: lambda self, *a, **k: None for nome in metodos})()
    assert isinstance(completo, protocolo)
    assert not isinstance(object(), protocolo)
    for faltando in metodos:
        parcial: Any = type(
            "Parcial", (), {nome: lambda self, *a, **k: None for nome in metodos - {faltando}}
        )()
        assert not isinstance(parcial, protocolo)


@pytest.mark.parametrize("valor", VALORES)
def test_valores_devolvidos_sao_dataclasses_imutaveis(valor: type) -> None:
    assert dataclasses.is_dataclass(valor)
    assert valor.__dataclass_params__.frozen is True  # type: ignore[attr-defined]


def test_o_modulo_nao_importa_as_camadas_de_cima() -> None:
    """O chat só define o contrato; quem implementa é `farol.api` (o import-linter confere)."""
    importados = {
        nome
        for nome, valor in vars(protocolos).items()
        if getattr(valor, "__module__", "").startswith(("farol.api", "farol.mapa", "farol.vistos"))
    }
    assert importados == set()
