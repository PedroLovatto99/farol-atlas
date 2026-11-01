"""Fallback de modelo do chat (D2): o que `create_agent` aceita, sem rede e sem modelo real.

Regressão da escolha feita (D2 em `specs/003-chat-alertas-viagem/research.md`): o plano B do
agente é o `ModelFallbackMiddleware`, que mantém o principal como `BaseChatModel` (o `bind_tools`
chega nele) e dispensa o `cast` que o `with_fallbacks` exigiria para o mypy.
"""

from collections.abc import Callable, Sequence
from typing import Any

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, tool


@tool
def consultar_algo(codigo: str) -> str:
    """Ferramenta de mentira, só para o `bind_tools` ser chamado de verdade."""
    return f"dados de {codigo}"


class ModeloFalso(GenericFakeChatModel):
    """Modelo de chat falso que aceita `bind_tools` (como os de verdade)."""

    def bind_tools(
        self, tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool], **_: Any
    ) -> Runnable[Any, AIMessage]:
        return self


class ModeloQueFalha(BaseChatModel):
    """Modelo principal fora do ar: toda chamada lança erro."""

    chamadas: int = 0
    pediu_ferramentas: bool = False

    @property
    def _llm_type(self) -> str:
        return "falho"

    def bind_tools(
        self, tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool], **_: Any
    ) -> Runnable[Any, AIMessage]:
        self.pediu_ferramentas = True
        return self

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> ChatResult:
        self.chamadas += 1
        raise RuntimeError("serviço de linguagem fora do ar")


def _alternativo(texto: str) -> ModeloFalso:
    return ModeloFalso(messages=iter([AIMessage(content=texto)]))


def _agente(principal: BaseChatModel, reserva: BaseChatModel | None = None) -> Any:
    """O agente como o chat o monta: com o alternativo, se houver, no middleware de fallback."""
    middleware = [] if reserva is None else [ModelFallbackMiddleware(reserva)]
    return create_agent(principal, tools=[consultar_algo], middleware=middleware)


def _responder(agente: Any) -> str:
    resultado = agente.invoke({"messages": [HumanMessage(content="oi")]})
    return str(resultado["messages"][-1].content)


def test_o_agente_usa_o_principal_quando_ele_responde() -> None:
    principal = _alternativo("do principal")
    reserva = _alternativo("da reserva")
    assert _responder(_agente(principal, reserva)) == "do principal"


def test_o_alternativo_responde_se_o_principal_falha() -> None:
    principal = ModeloQueFalha()
    reserva = _alternativo("resposta da reserva")
    assert _responder(_agente(principal, reserva)) == "resposta da reserva"
    assert principal.pediu_ferramentas  # o `bind_tools` chegou no principal
    assert principal.chamadas == 1


def test_sem_alternativo_o_erro_do_principal_chega_a_quem_chamou() -> None:
    with pytest.raises(RuntimeError, match="fora do ar"):
        _responder(_agente(ModeloQueFalha()))
