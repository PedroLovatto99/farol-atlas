"""`/mapa` e `/saude` e seus esquemas equivalem ao contrato em specs/.../contracts/openapi.yaml.

A normalização (tipos, anulabilidade, enums, referências) está em `conftest.py`.
"""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]


@pytest.mark.parametrize("caminho", ["/mapa", "/saude"])
def test_rota_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao", caminho: str
) -> None:
    esperada = contrato["paths"][caminho]["get"]
    obtida = gerado["paths"][f"{normalizacao.prefixo}{caminho}"]["get"]

    assert set(gerado["paths"][f"{normalizacao.prefixo}{caminho}"]) == {"get"}  # só leitura
    assert obtida["operationId"] == esperada["operationId"]
    assert set(obtida["responses"]) >= set(esperada["responses"])
    assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada)


@pytest.mark.parametrize("caminho", ["/mapa", "/saude"])
def test_schemas_da_rota_equivalem_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao", caminho: str
) -> None:
    raiz = normalizacao.resposta_200(contrato["paths"][caminho]["get"])
    esperado = normalizacao.fecho(raiz, contrato["components"]["schemas"])
    obtido = normalizacao.fecho(raiz, gerado["components"]["schemas"])

    assert set(obtido) == set(esperado)
    for nome in sorted(esperado):
        assert obtido[nome] == esperado[nome], f"schema {nome} difere do contrato"


def test_o_contrato_do_mapa_tem_os_schemas_esperados(
    contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    raiz = normalizacao.resposta_200(contrato["paths"]["/mapa"]["get"])
    assert raiz == "Mapa"
    assert set(normalizacao.fecho(raiz, contrato["components"]["schemas"])) == {
        "Mapa",
        "TerritorioNoMapa",
        "PostoNoMapa",
        "PaisSemPosto",
        "Regiao",
        "Nivel",
        "NivelRegional",
        "TipoTerritorio",
        "TipoPosto",
    }
