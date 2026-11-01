"""Fachada do modelo de linguagem do chat (D2): o único lugar que sabe como ele é criado.

O principal vem de `LLM_CHAT` (vazio = o mesmo do classificador) e o alternativo, se houver, de
`LLM_CHAT_ALTERNATIVO`. Os dois usam só a chave do chat (`GOOGLE_API_KEY_CHAT`): a cota do chat
fica no projeto dele e nunca come a da coleta. O plano B entra no agente pelo
`ModelFallbackMiddleware` (veja `agente.py`), não por `with_fallbacks`: assim o principal continua
um `BaseChatModel` de verdade (D2, decisão da T026).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from farol.infra import Configuracoes, argumentos_do_modelo


class ModeloDoChatIndisponivel(RuntimeError):
    """Nenhum modelo configurado para o chat."""


@dataclass(frozen=True)
class ModeloDoChat:
    principal: BaseChatModel
    alternativo: BaseChatModel | None = None


def criar_modelo_do_chat(
    configuracoes: Configuracoes, *, fabrica: Callable[..., Any] = init_chat_model
) -> ModeloDoChat:
    """Os modelos do chat. Lança `ChaveDoChatAusente` (Google sem a chave do chat) e
    `ModeloDoChatIndisponivel` (nenhum modelo configurado)."""
    nome = (configuracoes.llm_chat or configuracoes.llm_classificador or "").strip()
    if not nome:
        raise ModeloDoChatIndisponivel("defina LLM_CHAT (ou LLM_CLASSIFICADOR) para ligar o chat")

    def criar(nome_do_modelo: str) -> BaseChatModel:
        argumentos = argumentos_do_modelo(nome_do_modelo, configuracoes, chave_do_chat=True)
        modelo: BaseChatModel = fabrica(nome_do_modelo, **argumentos)
        return modelo

    alternativo = configuracoes.llm_chat_alternativo.strip()
    return ModeloDoChat(criar(nome), criar(alternativo) if alternativo else None)
