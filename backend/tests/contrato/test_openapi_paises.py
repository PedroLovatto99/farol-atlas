"""`/paises/{codigo}` e seus esquemas equivalem ao contrato em specs/.../contracts/openapi.yaml.

Reaproveita a normalização de `test_openapi_mapa.py`, copiada aqui porque os testes não formam um
pacote importável (`--import-mode=importlib`).
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
CAMINHO = "/paises/{codigo}"
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
def test_rota_equivale_ao_contrato(contrato: Documento, gerado: Documento) -> None:
    esperada = contrato["paths"][CAMINHO]["get"]
    obtida = gerado["paths"][f"{PREFIXO}{CAMINHO}"]["get"]

    assert set(gerado["paths"][f"{PREFIXO}{CAMINHO}"]) == {"get"}  # só leitura
    assert obtida["operationId"] == esperada["operationId"] == "obterPais"
    assert set(obtida["responses"]) >= set(esperada["responses"])
    assert resposta_200(obtida) == resposta_200(esperada) == "Pais"


def test_erros_da_rota_usam_o_esquema_erro(contrato: Documento, gerado: Documento) -> None:
    obtida = gerado["paths"][f"{PREFIXO}{CAMINHO}"]["get"]["responses"]
    for status in ("404", "422"):
        schema = obtida[status]["content"]["application/json"]["schema"]
        assert _nome_da_referencia(schema["$ref"]) == "Erro"


def test_parametro_codigo_equivale_ao_contrato(contrato: Documento, gerado: Documento) -> None:
    (esperado,) = contrato["paths"][CAMINHO]["get"]["parameters"]
    (obtido,) = gerado["paths"][f"{PREFIXO}{CAMINHO}"]["get"]["parameters"]

    assert (obtido["name"], obtido["in"], obtido["required"]) == (
        esperado["name"],
        esperado["in"],
        esperado["required"],
    )
    assert obtido["schema"]["type"] == esperado["schema"]["type"] == "string"
    assert obtido["schema"]["pattern"] == esperado["schema"]["pattern"]


def test_schemas_da_rota_equivalem_ao_contrato(contrato: Documento, gerado: Documento) -> None:
    raiz = resposta_200(contrato["paths"][CAMINHO]["get"])
    esperado = fecho(raiz, contrato["components"]["schemas"])
    obtido = fecho(raiz, gerado["components"]["schemas"])

    assert set(obtido) == set(esperado)
    for nome in sorted(esperado):
        assert obtido[nome] == esperado[nome], f"schema {nome} difere do contrato"


def test_o_contrato_do_painel_tem_os_schemas_esperados(contrato: Documento) -> None:
    assert set(fecho("Pais", contrato["components"]["schemas"])) >= {
        "Pais",
        "AlertaDoPais",
        "PostoNoPainel",
        "FontePostos",
        "Regiao",
        "Nivel",
        "NivelRegional",
        "TipoTerritorio",
        "TipoPosto",
    }
