"""CORS por rota: só `POST /api/v1/chat` aceita escrita, com `Content-Type`; o resto, só GET."""

from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from farol.api.app import criar_app
from farol.infra import Configuracoes

PERMITIDA = "https://farol.exemplo"
DE_FORA = "https://outro.exemplo"


def cliente(**campos: Any) -> TestClient:
    config = Configuracoes(
        database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"),
        cors_origens=[PERMITIDA],
        limite_pedidos_por_minuto=0,
        **campos,
    )
    return TestClient(criar_app(config), raise_server_exceptions=False)


def pre_voo(caminho: str, origem: str, metodo: str, cabecalhos: str | None = None) -> Any:
    pedido = {"Origin": origem, "Access-Control-Request-Method": metodo}
    if cabecalhos:
        pedido["Access-Control-Request-Headers"] = cabecalhos
    return cliente().options(caminho, headers=pedido)


def test_pre_voo_do_post_no_chat_da_origem_permitida() -> None:
    resposta = pre_voo("/api/v1/chat", PERMITIDA, "POST", "content-type")

    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-origin"] == PERMITIDA
    assert resposta.headers["access-control-allow-methods"] == "POST"
    assert "content-type" in resposta.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in resposta.headers


def test_pre_voo_do_chat_de_origem_nao_permitida() -> None:
    resposta = pre_voo("/api/v1/chat", DE_FORA, "POST", "content-type")
    assert resposta.status_code == 400
    assert "access-control-allow-origin" not in resposta.headers


def test_pre_voo_de_outro_cabecalho_no_chat_e_recusado() -> None:
    resposta = pre_voo("/api/v1/chat", PERMITIDA, "POST", "authorization")
    assert resposta.status_code == 400


def test_delete_no_chat_e_recusado_pelo_cors() -> None:
    resposta = pre_voo("/api/v1/chat", PERMITIDA, "DELETE")
    assert resposta.status_code == 400
    assert "DELETE" not in resposta.headers.get("access-control-allow-methods", "")


def test_post_continua_recusado_nas_rotas_de_leitura() -> None:
    for caminho in ("/api/v1/mapa", "/api/v1/paises/IR", "/api/v1/vistos", "/api/v1/saude"):
        resposta = pre_voo(caminho, PERMITIDA, "POST", "content-type")
        assert resposta.status_code == 400, caminho
        assert "POST" not in resposta.headers.get("access-control-allow-methods", "")


def test_leitura_continua_com_get_e_sem_cabecalhos() -> None:
    resposta = pre_voo("/api/v1/mapa", PERMITIDA, "GET")
    assert resposta.status_code == 200
    assert resposta.headers["access-control-allow-methods"] == "GET"


def test_respostas_do_chat_expoem_o_retry_after_para_o_navegador() -> None:
    """O 503 (e, com a US4, o 429) precisa sair com CORS para o navegador ler."""
    resposta = cliente(chat_habilitado=False).post(
        "/api/v1/chat",
        json={"pergunta": "oi", "historico": []},
        headers={"Origin": PERMITIDA},
    )
    assert resposta.status_code == 503
    assert resposta.headers["access-control-allow-origin"] == PERMITIDA
    assert "retry-after" in resposta.headers["access-control-expose-headers"].lower()
