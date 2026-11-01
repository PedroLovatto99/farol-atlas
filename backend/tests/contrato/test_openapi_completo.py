"""Regressão final de ponta a ponta: o OpenAPI gerado equivale POR INTEIRO ao contrato (o COMPLETO
da API v1.2, da feature 003: o da 002 mais a rota `POST /chat`).

Repete de propósito o que os testes rota a rota verificam em partes. Aqui o que vale é o conjunto:
nenhuma rota, esquema, parâmetro ou resposta a mais ou a menos, e a única escrita é a pergunta do
chat (princípio VIII).
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

METODOS_DE_ESCRITA = {"post", "put", "patch", "delete"}
ESCRITA_PERMITIDA = {("/chat", "post")}


def caminhos_gerados(gerado: Documento, prefixo: str) -> dict[str, Documento]:
    """Rotas do FastAPI sem o prefixo `/api/v1`, que no contrato vem em `servers`."""
    return {caminho.removeprefix(prefixo): rota for caminho, rota in gerado["paths"].items()}


def parametros(operacao: Documento) -> set[tuple[str, str, bool]]:
    return {(p["name"], p["in"], p["required"]) for p in operacao.get("parameters", [])}


def operacoes(documento: Documento) -> dict[tuple[str, str], Documento]:
    return {
        (caminho, metodo): operacao
        for caminho, rota in documento["paths"].items()
        for metodo, operacao in rota.items()
    }


def test_o_prefixo_do_contrato_e_o_da_api(
    contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    assert [servidor["url"] for servidor in contrato["servers"]] == [normalizacao.prefixo]


def test_as_mesmas_rotas_e_a_unica_escrita_e_o_chat(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = caminhos_gerados(gerado, normalizacao.prefixo)

    assert set(obtidas) == set(contrato["paths"])
    for caminho, rota in obtidas.items():
        assert set(rota) == set(contrato["paths"][caminho]), caminho
        escritas = {(caminho, m) for m in rota if m in METODOS_DE_ESCRITA}
        assert escritas <= ESCRITA_PERMITIDA, f"{caminho} aceita escrita: {escritas}"
    assert set(obtidas["/chat"]) == {"post"}


def test_cada_operacao_tem_o_mesmo_id_as_mesmas_respostas_e_os_mesmos_parametros(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = operacoes({"paths": caminhos_gerados(gerado, normalizacao.prefixo)})

    for chave, esperada in operacoes(contrato).items():
        obtida = obtidas[chave]
        assert obtida["operationId"] == esperada["operationId"], chave
        assert set(obtida["responses"]) >= set(esperada["responses"]), chave
        assert parametros(obtida) == parametros(esperada), chave
        if chave[1] == "get":
            assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada), chave


def test_as_respostas_json_usam_o_mesmo_esquema_do_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    obtidas = operacoes({"paths": caminhos_gerados(gerado, normalizacao.prefixo)})
    nome = normalizacao.nome_da_referencia

    for chave, operacao in operacoes(contrato).items():
        for status, resposta in operacao["responses"].items():
            if status == "200":
                continue
            esperado = resposta["content"]["application/json"]["schema"]["$ref"]
            obtido = obtidas[chave]["responses"][status]["content"]["application/json"]
            assert nome(obtido["schema"]["$ref"]) == nome(esperado), f"{chave} {status}"


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
    raizes: set[str] = set()
    for rota in contrato["paths"].values():
        for operacao in rota.values():
            raizes |= normalizacao.referencias(operacao)
    usados: set[str] = set()
    for raiz in raizes:
        usados |= set(normalizacao.fecho(raiz, esquemas))
    assert usados == set(esquemas)
