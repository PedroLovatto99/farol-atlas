"""`/paises/{codigo}` e seus esquemas equivalem ao contrato em specs/.../contracts/openapi.yaml.

A normalização (tipos, anulabilidade, enums, referências) está em `conftest.py`.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

CAMINHO = "/paises/{codigo}"


def test_rota_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperada = contrato["paths"][CAMINHO]["get"]
    obtida = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]["get"]

    assert set(gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]) == {"get"}  # só leitura
    assert obtida["operationId"] == esperada["operationId"] == "obterPais"
    assert set(obtida["responses"]) >= set(esperada["responses"])
    assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada) == "Pais"


def test_erros_da_rota_usam_o_esquema_erro(gerado: Documento, normalizacao: "Normalizacao") -> None:
    obtida = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]["get"]["responses"]
    for status in ("404", "422"):
        schema = obtida[status]["content"]["application/json"]["schema"]
        assert normalizacao.nome_da_referencia(schema["$ref"]) == "Erro"


def test_parametro_codigo_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    (esperado,) = contrato["paths"][CAMINHO]["get"]["parameters"]
    (obtido,) = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]["get"]["parameters"]

    assert (obtido["name"], obtido["in"], obtido["required"]) == (
        esperado["name"],
        esperado["in"],
        esperado["required"],
    )
    assert obtido["schema"]["type"] == esperado["schema"]["type"] == "string"
    assert obtido["schema"]["pattern"] == esperado["schema"]["pattern"]


def test_schemas_da_rota_equivalem_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    raiz = normalizacao.resposta_200(contrato["paths"][CAMINHO]["get"])
    esperado = normalizacao.fecho(raiz, contrato["components"]["schemas"])
    obtido = normalizacao.fecho(raiz, gerado["components"]["schemas"])

    assert set(obtido) == set(esperado)
    for nome in sorted(esperado):
        assert obtido[nome] == esperado[nome], f"schema {nome} difere do contrato"


def test_o_contrato_do_painel_tem_os_schemas_esperados(
    contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    assert set(normalizacao.fecho("Pais", contrato["components"]["schemas"])) >= {
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
