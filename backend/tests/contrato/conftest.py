"""Base dos testes de contrato: o OpenAPI desenhado em specs/ e o gerado pelo FastAPI.

O contrato é o COMPLETO da API v1.1 (feature 002), que contém o da 001 por inteiro mais a rota
`/vistos` e o campo `Pais.visto`. O arquivo da 001 fica como histórico da v1.0, e o teste
`test_contrato_002_preserva_001.py` falha se a parte da 001 mudar.

A comparação ignora o que não é contrato (títulos, descrições, exemplos) e escreve os dois lados
na mesma forma: tipos, anulabilidade, formatos, enums, propriedades, obrigatórios e referências.
Os testes não formam um pacote importável (`--import-mode=importlib`), então o que é comum chega
por fixtures: `contrato`, `gerado` e `normalizacao`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from farol.api.exportar_openapi import gerar_openapi

CONTRATO = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "002-visto-brasileiros"
    / "contracts"
    / "openapi.yaml"
)
PREFIXO = "/api/v1"

Documento = dict[str, Any]


def nome_da_referencia(referencia: str) -> str:
    return referencia.rsplit("/", 1)[-1]


def esboco(schema: Documento) -> Documento:
    """A parte do schema que é contrato, na mesma forma para o YAML e para o FastAPI."""
    if "$ref" in schema:
        return {"ref": nome_da_referencia(schema["$ref"])}

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
        achadas.add(nome_da_referencia(schema["$ref"]))
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
    return nome_da_referencia(schema["$ref"])


@dataclass(frozen=True)
class Normalizacao:
    """As funções acima, entregues por fixture."""

    prefixo: str = PREFIXO

    esboco = staticmethod(esboco)
    referencias = staticmethod(referencias)
    fecho = staticmethod(fecho)
    resposta_200 = staticmethod(resposta_200)
    nome_da_referencia = staticmethod(nome_da_referencia)


@pytest.fixture(scope="session")
def contrato() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    return carregado


@pytest.fixture(scope="session")
def gerado() -> Documento:
    return gerar_openapi()


@pytest.fixture(scope="session")
def normalizacao() -> Normalizacao:
    return Normalizacao()
