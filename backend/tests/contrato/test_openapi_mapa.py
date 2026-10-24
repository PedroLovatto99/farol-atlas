"""O OpenAPI gerado pelo FastAPI equivale ao contrato desenhado em specs/.../contracts/openapi.yaml.

A comparação ignora o que não é contrato (títulos, descrições, exemplos) e escreve os dois lados
na mesma forma: tipos, anulabilidade, formatos, enums, propriedades, obrigatórios e referências.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from farol.api.exportar_openapi import gerar_openapi

CONTRATO = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "001-mapa-alertas-viagem"
    / "contracts"
    / "openapi.yaml"
)
PREFIXO = "/api/v1"

Documento = dict[str, Any]


@pytest.fixture(scope="module")
def contrato() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    return carregado


@pytest.fixture(scope="module")
def gerado() -> Documento:
    return gerar_openapi()


# --------------------------------------------------------------------------- normalização
def _nome_da_referencia(referencia: str) -> str:
    return referencia.rsplit("/", 1)[-1]


def esboco(schema: Documento) -> Documento:
    """A parte do schema que é contrato, na mesma forma para o YAML e para o FastAPI."""
    if "$ref" in schema:
        return {"ref": _nome_da_referencia(schema["$ref"])}

    resultado: Documento = {}
    anulavel = False

    if "anyOf" in schema:
        partes = [esboco(p) for p in schema["anyOf"]]
        anulavel = any(p == {"tipos": ["null"]} for p in partes)
        restantes = [p for p in partes if p != {"tipos": ["null"]}]
        if len(restantes) != 1:
            return {"anyOf": sorted(restantes, key=str), "anulavel": anulavel}
        resultado.update(restantes[0])

    tipos = schema.get("type")
    if isinstance(tipos, list):
        anulavel = anulavel or "null" in tipos
        tipos = [t for t in tipos if t != "null"] or ["null"]
    elif isinstance(tipos, str):
        tipos = [tipos]
    if tipos:
        resultado["tipos"] = sorted(tipos)

    if "format" in schema:
        resultado["formato"] = schema["format"]
    if "enum" in schema:
        resultado["enum"] = sorted(schema["enum"])
    if "const" in schema:
        resultado["enum"] = [schema["const"]]
    if "items" in schema:
        resultado["itens"] = esboco(schema["items"])
    if "properties" in schema:
        resultado["propriedades"] = {n: esboco(p) for n, p in schema["properties"].items()}
        resultado["obrigatorios"] = sorted(schema.get("required", []))
    if anulavel:
        resultado["anulavel"] = True
    return resultado


def referencias(schema: Documento) -> set[str]:
    """Nomes de tudo o que o schema referencia, em qualquer profundidade."""
    achadas: set[str] = set()
    if isinstance(schema.get("$ref"), str):
        achadas.add(_nome_da_referencia(schema["$ref"]))
    for valor in schema.values():
        if isinstance(valor, dict):
            achadas |= referencias(valor)
        elif isinstance(valor, list):
            for elemento in valor:
                if isinstance(elemento, dict):
                    achadas |= referencias(elemento)
    return achadas


def fecho(raiz: str, esquemas: Documento) -> dict[str, Documento]:
    """O schema `raiz` e todos os que ele alcança."""
    vistos: dict[str, Documento] = {}
    pendentes = [raiz]
    while pendentes:
        nome = pendentes.pop()
        if nome in vistos:
            continue
        vistos[nome] = esboco(esquemas[nome])
        pendentes += sorted(referencias(esquemas[nome]))
    return vistos


def resposta_200(operacao: Documento) -> str:
    schema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    return _nome_da_referencia(schema["$ref"])


# --------------------------------------------------------------------------- comparação
@pytest.mark.parametrize("caminho", ["/mapa", "/saude"])
def test_rota_equivale_ao_contrato(contrato: Documento, gerado: Documento, caminho: str) -> None:
    esperada = contrato["paths"][caminho]["get"]
    obtida = gerado["paths"][f"{PREFIXO}{caminho}"]["get"]

    assert set(gerado["paths"][f"{PREFIXO}{caminho}"]) == {"get"}  # só leitura
    assert obtida["operationId"] == esperada["operationId"]
    assert set(obtida["responses"]) >= set(esperada["responses"])
    assert resposta_200(obtida) == resposta_200(esperada)


@pytest.mark.parametrize("caminho", ["/mapa", "/saude"])
def test_schemas_da_rota_equivalem_ao_contrato(
    contrato: Documento, gerado: Documento, caminho: str
) -> None:
    raiz = resposta_200(contrato["paths"][caminho]["get"])
    esperado = fecho(raiz, contrato["components"]["schemas"])
    obtido = fecho(raiz, gerado["components"]["schemas"])

    assert set(obtido) == set(esperado)
    for nome in sorted(esperado):
        assert obtido[nome] == esperado[nome], f"schema {nome} difere do contrato"


def test_o_contrato_do_mapa_tem_os_schemas_esperados(contrato: Documento) -> None:
    raiz = resposta_200(contrato["paths"]["/mapa"]["get"])
    assert raiz == "Mapa"
    assert set(fecho(raiz, contrato["components"]["schemas"])) == {
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
