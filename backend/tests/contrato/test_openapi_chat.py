"""`POST /chat` e os esquemas do chat equivalem ao contrato v1.2 (specs/003-.../contracts).

A normalização (tipos, anulabilidade, enums, referências) está em `conftest.py`.
"""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

ESQUEMAS_DO_CHAT = (
    "PerguntaDoChat",
    "MensagemDoHistorico",
    "ErroDoChat",
    "EventoProgresso",
    "SituacaoDaResposta",
    "EventoResposta",
    "EventoErro",
    "CartaoDoChat",
    "CartaoDeNivel",
    "CartaoDeVisto",
    "CartaoDePostos",
    "PaisDaLista",
    "CartaoDeLista",
    "CitacaoDoChat",
)


@pytest.fixture
def operacao_gerada(gerado: Documento, normalizacao: "Normalizacao") -> Documento:
    rota: Documento = gerado["paths"][f"{normalizacao.prefixo}/chat"]
    assert set(rota) == {"post"}
    operacao: Documento = rota["post"]
    return operacao


@pytest.fixture
def operacao_do_contrato(contrato: Documento) -> Documento:
    operacao: Documento = contrato["paths"]["/chat"]["post"]
    return operacao


def test_mesmo_id_e_mesmo_corpo(
    operacao_gerada: Documento, operacao_do_contrato: Documento, normalizacao: "Normalizacao"
) -> None:
    assert (
        operacao_gerada["operationId"] == operacao_do_contrato["operationId"] == "perguntarAoChat"
    )
    corpo = operacao_gerada["requestBody"]
    assert corpo["required"] is True
    esquema = corpo["content"]["application/json"]["schema"]
    assert normalizacao.nome_da_referencia(esquema["$ref"]) == "PerguntaDoChat"


def test_o_200_e_um_fluxo_de_eventos_como_no_contrato(
    operacao_gerada: Documento, operacao_do_contrato: Documento
) -> None:
    gerado = operacao_gerada["responses"]["200"]["content"]
    esperado = operacao_do_contrato["responses"]["200"]["content"]
    assert set(gerado) == set(esperado) == {"text/event-stream"}
    assert gerado["text/event-stream"]["itemSchema"] == esperado["text/event-stream"]["itemSchema"]


@pytest.mark.parametrize(
    ("status", "esquema"), [("422", "Erro"), ("429", "ErroDoChat"), ("503", "ErroDoChat")]
)
def test_erros_antes_do_fluxo_sao_json(
    operacao_gerada: Documento, normalizacao: "Normalizacao", status: str, esquema: str
) -> None:
    conteudo = operacao_gerada["responses"][status]["content"]
    assert set(conteudo) == {"application/json"}
    assert (
        normalizacao.nome_da_referencia(conteudo["application/json"]["schema"]["$ref"]) == esquema
    )


def test_x_eventos_publicado(operacao_gerada: Documento, operacao_do_contrato: Documento) -> None:
    assert operacao_gerada["x-eventos"] == operacao_do_contrato["x-eventos"]


@pytest.mark.parametrize("nome", ESQUEMAS_DO_CHAT)
def test_esquema_do_chat_igual_ao_do_contrato(
    nome: str, contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperado = contrato["components"]["schemas"][nome]
    obtido = gerado["components"]["schemas"][nome]
    assert normalizacao.esboco(obtido) == normalizacao.esboco(esperado)


def test_os_cartoes_sao_escolhidos_pelo_tipo(gerado: Documento) -> None:
    cartao = gerado["components"]["schemas"]["CartaoDoChat"]
    assert cartao["discriminator"]["propertyName"] == "tipo"
    assert set(cartao["discriminator"]["mapping"]) == {"nivel", "visto", "postos", "lista"}
