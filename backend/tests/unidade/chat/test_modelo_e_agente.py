"""Fachada `criar_modelo_do_chat` e o agente: modelo, chave do chat, fallback, prompt e limites.

Sem rede: a fábrica de modelos é falsa e o modelo de chat é o roteirizado dos testes.
"""

from typing import Any

import pytest
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.messages import HumanMessage, SystemMessage
from tests.falsos_chat import ModeloDeChatFalso, responder

from farol.chat.agente import (
    LIMITE_DE_CHAMADAS_AO_MODELO,
    LIMITE_DE_CHAMADAS_DE_FERRAMENTA,
    PROMPT_DO_SISTEMA,
    RespostaDoModelo,
    criar_agente,
    middlewares_do_agente,
)
from farol.chat.modelo import ModeloDoChat, ModeloDoChatIndisponivel, criar_modelo_do_chat
from farol.infra import ChaveDoChatAusente, Configuracoes

URL = "postgresql+psycopg://farol:farol@postgres:5432/farol"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in (
        "GOOGLE_API_KEY",
        "GOOGLE_API_KEY_CHAT",
        "LLM_CHAT",
        "LLM_CHAT_ALTERNATIVO",
        "LLM_CLASSIFICADOR",
    ):
        monkeypatch.delenv(nome, raising=False)


def configuracoes(**campos: Any) -> Configuracoes:
    return Configuracoes(_env_file=None, database_url=URL, **campos)


class Fabrica:
    def __init__(self) -> None:
        self.pedidos: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, nome: str, **argumentos: Any) -> ModeloDeChatFalso:
        self.pedidos.append((nome, argumentos))
        return ModeloDeChatFalso()


# ------------------------------------------------------------------------------ modelo
def test_principal_com_a_chave_do_chat() -> None:
    fabrica = Fabrica()
    modelo = criar_modelo_do_chat(
        configuracoes(
            llm_chat="google_genai:modelo-do-chat",
            google_api_key="chave-da-coleta",
            google_api_key_chat="chave-do-chat",
        ),
        fabrica=fabrica,
    )

    assert isinstance(modelo, ModeloDoChat) and modelo.alternativo is None
    [(nome, argumentos)] = fabrica.pedidos
    assert nome == "google_genai:modelo-do-chat"
    assert argumentos["api_key"] == "chave-do-chat"
    assert argumentos["temperature"] == 0


def test_llm_chat_vazio_usa_o_modelo_do_classificador() -> None:
    fabrica = Fabrica()
    criar_modelo_do_chat(
        configuracoes(llm_classificador="google_genai:o-do-classificador", google_api_key_chat="k"),
        fabrica=fabrica,
    )
    assert fabrica.pedidos[0][0] == "google_genai:o-do-classificador"


def test_alternativo_vem_de_llm_chat_alternativo() -> None:
    fabrica = Fabrica()
    modelo = criar_modelo_do_chat(
        configuracoes(
            llm_chat="google_genai:a",
            llm_chat_alternativo="google_genai:b",
            google_api_key_chat="k",
        ),
        fabrica=fabrica,
    )
    assert modelo.alternativo is not None
    assert [nome for nome, _ in fabrica.pedidos] == ["google_genai:a", "google_genai:b"]
    assert all(argumentos["api_key"] == "k" for _, argumentos in fabrica.pedidos)


def test_sem_chave_do_chat_nao_cai_na_da_coleta() -> None:
    with pytest.raises(ChaveDoChatAusente):
        criar_modelo_do_chat(
            configuracoes(llm_chat="google_genai:a", google_api_key="chave-da-coleta"),
            fabrica=Fabrica(),
        )


def test_sem_modelo_configurado_o_chat_fica_indisponivel() -> None:
    with pytest.raises(ModeloDoChatIndisponivel):
        criar_modelo_do_chat(configuracoes(llm_classificador="", llm_chat=""), fabrica=Fabrica())


# ------------------------------------------------------------------------------ agente
def test_limites_duros_e_fallback_no_middleware() -> None:
    reserva = ModeloDeChatFalso()
    middlewares = middlewares_do_agente(ModeloDoChat(ModeloDeChatFalso(), reserva))

    tipos = [type(m) for m in middlewares]
    assert ModelCallLimitMiddleware in tipos and ToolCallLimitMiddleware in tipos
    assert ModelFallbackMiddleware in tipos
    assert LIMITE_DE_CHAMADAS_AO_MODELO == 4 and LIMITE_DE_CHAMADAS_DE_FERRAMENTA == 6
    sem_reserva = middlewares_do_agente(ModeloDoChat(ModeloDeChatFalso(), None))
    assert ModelFallbackMiddleware not in [type(m) for m in sem_reserva]


def test_o_prompt_do_sistema_tem_as_regras_em_portugues() -> None:
    prompt = PROMPT_DO_SISTEMA.lower()
    assert "<<<dados" in prompt  # o que vem das ferramentas é dado, nunca ordem
    assert "nunca" in prompt and "seguro" in prompt  # nada de recomendação própria
    assert "não encontrei" in prompt and "portal consular" in prompt
    assert "português" in prompt
    assert "buscar_nos_alertas" in prompt
    for inexistente in ("consultar_visto", "consultar_postos", "listar_paises"):
        assert inexistente not in prompt  # nada de ferramenta que este agente não tem


def test_resposta_estruturada_do_modelo() -> None:
    resposta = RespostaDoModelo(texto="ok", assuntos=["alertas"], situacao="resposta")
    assert resposta.situacao == "resposta"
    with pytest.raises(ValueError):
        RespostaDoModelo(texto="ok", assuntos=["alertas"], situacao="pergunta_de_volta")
    with pytest.raises(ValueError):
        RespostaDoModelo(texto="x" * 2001, assuntos=[], situacao="resposta")


def test_o_agente_entrega_a_resposta_estruturada_e_manda_o_prompt() -> None:
    falso = ModeloDeChatFalso(roteiro=[responder("Nada a dizer.", situacao="nao_encontrei")])
    agente = criar_agente(ModeloDoChat(falso, None), ferramentas=[])

    final = agente.invoke({"messages": [HumanMessage(content="oi")]})

    assert final["structured_response"] == RespostaDoModelo(
        texto="Nada a dizer.", assuntos=["alertas"], situacao="nao_encontrei"
    )
    [mensagens] = falso.recebidas
    assert isinstance(mensagens[0], SystemMessage)
    assert mensagens[0].content == PROMPT_DO_SISTEMA
