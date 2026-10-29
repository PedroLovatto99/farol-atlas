"""Regressão final de ponta a ponta: o OpenAPI gerado equivale POR INTEIRO ao contrato (o COMPLETO
da API v1.1, da feature 002: o da 001 mais `/vistos` e `Pais.visto`).

Repete de propósito o que `test_openapi_mapa.py`, `test_openapi_paises.py` e
`test_openapi_vistos.py` verificam em partes (rota a rota). Aqui o que vale é o conjunto: nenhuma
rota, esquema, parâmetro ou resposta a mais ou a menos, e nenhuma rota que não seja de leitura.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

METODOS_DE_ESCRITA = {"post", "put", "patch", "delete"}


def caminhos_gerados(gerado: Documento, prefixo: str) -> dict[str, Documento]:
    """Rotas do FastAPI sem o prefixo `/api/v1`, que no contrato vem em `servers`."""
    return {caminho.removeprefix(prefixo): rota for caminho, rota in gerado["paths"].items()}


def parametros(operacao: Documento) -> set[tuple[str, str, bool]]:
    return {(p["name"], p["in"], p["required"]) for p in operacao.get("parameters", [])}


def test_o_prefixo_do_contrato_e_o_da_api(
    contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    assert [servidor["url"] for servidor in contrato["servers"]] == [normalizacao.prefixo]


def test_as_mesmas_rotas_e_so_de_leitura(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = caminhos_gerados(gerado, normalizacao.prefixo)

    assert set(obtidas) == set(contrato["paths"])
    for caminho, rota in obtidas.items():
        assert set(rota) == {"get"}, f"{caminho} aceita mais do que leitura: {set(rota)}"
        assert not set(rota) & METODOS_DE_ESCRITA


def test_cada_rota_tem_a_mesma_operacao_as_mesmas_respostas_e_os_mesmos_parametros(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = caminhos_gerados(gerado, normalizacao.prefixo)

    for caminho, rota in contrato["paths"].items():
        esperada = rota["get"]
        obtida = obtidas[caminho]["get"]
        assert obtida["operationId"] == esperada["operationId"], caminho
        assert set(obtida["responses"]) >= set(esperada["responses"]), caminho
        assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada), caminho
        assert parametros(obtida) == parametros(esperada), caminho


def test_as_respostas_de_erro_usam_o_mesmo_esquema_do_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = caminhos_gerados(gerado, normalizacao.prefixo)
    nome = normalizacao.nome_da_referencia

    for caminho, rota in contrato["paths"].items():
        for status, resposta in rota["get"]["responses"].items():
            if status == "200":
                continue
            esperado = resposta["content"]["application/json"]["schema"]["$ref"]
            obtido = obtidas[caminho]["get"]["responses"][status]["content"]["application/json"]
            assert nome(obtido["schema"]["$ref"]) == nome(esperado), f"{caminho} {status}"


def test_os_mesmos_esquemas_e_cada_um_igual_ao_do_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperados = contrato["components"]["schemas"]
    obtidos = gerado["components"]["schemas"]

    assert set(obtidos) == set(esperados)
    for nome in sorted(esperados):
        assert normalizacao.esboco(obtidos[nome]) == normalizacao.esboco(esperados[nome]), (
            f"schema {nome} difere do contrato"
        )


def test_nenhum_esquema_do_contrato_fica_sem_uso(
    contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    esquemas = contrato["components"]["schemas"]
    usados: set[str] = set()
    for rota in contrato["paths"].values():
        for resposta in rota["get"]["responses"].values():
            raiz = resposta["content"]["application/json"]["schema"]["$ref"]
            usados |= set(normalizacao.fecho(normalizacao.nome_da_referencia(raiz), esquemas))
    assert usados == set(esquemas)
