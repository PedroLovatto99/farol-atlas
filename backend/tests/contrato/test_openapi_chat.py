"""`POST /chat` e os esquemas do chat equivalem ao contrato em specs/.../contracts.

A normalização (tipos, anulabilidade, enums, referências) está em `conftest.py`.
"""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

CAMINHO = "/chat"
ESQUEMAS_DO_CHAT = ("PerguntaDoChat", "RespostaDoChat", "TrechoDoChat", "TipoDeRespostaDoChat")


def test_rota_do_chat_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperada = contrato["paths"][CAMINHO]["post"]
    rota = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]
    obtida = rota["post"]

    assert set(rota) == {"post"}
    assert obtida["operationId"] == esperada["operationId"] == "perguntarAoChat"
    assert set(obtida["responses"]) == set(esperada["responses"]) == {"200", "422", "429"}
    assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada)
    assert normalizacao.resposta_200(obtida) == "RespostaDoChat"


def test_o_corpo_e_obrigatorio_e_e_a_pergunta(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    for documento, caminho in ((contrato, CAMINHO), (gerado, f"{normalizacao.prefixo}{CAMINHO}")):
        corpo = documento["paths"][caminho]["post"]["requestBody"]
        assert corpo["required"] is True
        schema = corpo["content"]["application/json"]["schema"]
        assert normalizacao.nome_da_referencia(schema["$ref"]) == "PerguntaDoChat"


@pytest.mark.parametrize("status", ["422", "429"])
def test_os_erros_usam_o_esquema_erro(
    gerado: Documento, normalizacao: "Normalizacao", status: str
) -> None:
    resposta = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]["post"]["responses"][status]
    schema = resposta["content"]["application/json"]["schema"]
    assert normalizacao.nome_da_referencia(schema["$ref"]) == "Erro"


def test_o_429_traz_o_retry_after(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperado = contrato["paths"][CAMINHO]["post"]["responses"]["429"]["headers"]
    obtido = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]["post"]["responses"]["429"]
    assert obtido["headers"]["Retry-After"]["schema"] == esperado["Retry-After"]["schema"]


@pytest.mark.parametrize("nome", ESQUEMAS_DO_CHAT)
def test_cada_esquema_do_chat_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao", nome: str
) -> None:
    esperado = contrato["components"]["schemas"][nome]
    obtido = gerado["components"]["schemas"][nome]

    assert normalizacao.esboco(obtido) == normalizacao.esboco(esperado), (
        f"schema {nome} difere do contrato"
    )


def test_a_pergunta_tem_os_limites_do_contrato(contrato: Documento, gerado: Documento) -> None:
    for documento in (contrato, gerado):
        esquema = documento["components"]["schemas"]["PerguntaDoChat"]
        assert esquema["additionalProperties"] is False
        assert esquema["properties"]["pergunta"]["minLength"] == 1
        assert esquema["properties"]["pergunta"]["maxLength"] == 300


def test_os_tipos_de_resposta_sao_exatamente_os_do_contrato(gerado: Documento) -> None:
    assert set(gerado["components"]["schemas"]["TipoDeRespostaDoChat"]["enum"]) == {
        "alerta",
        "visto",
        "alerta_e_visto",
        "qual_dos_paises",
        "pedir_pais",
        "um_pais_por_vez",
        "brasil",
        "fora_do_assunto",
        "reformular",
    }


def test_a_versao_da_api_e_a_do_contrato(contrato: Documento, gerado: Documento) -> None:
    assert gerado["info"]["version"] == contrato["info"]["version"] == "1.2.0"
