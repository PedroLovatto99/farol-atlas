"""Argumentos de criação do modelo de LLM, a partir de "provedor:modelo".

Fica na infra para o classificador e o tradutor montarem o modelo do mesmo jeito. Não importa
LangChain: quem cria o modelo (`init_chat_model`) é cada módulo.
"""

from typing import Any

from farol.infra.config import Configuracoes

TEMPO_LIMITE_SEGUNDOS = 90


class ChaveDoChatAusente(RuntimeError):
    """O chat usa o Google e `GOOGLE_API_KEY_CHAT` não está definida."""


def argumentos_do_modelo(
    nome: str, configuracoes: Configuracoes, *, chave_do_chat: bool = False
) -> dict[str, Any]:
    """Argumentos de `init_chat_model` para o modelo `nome` ("provedor:modelo"), temperatura 0.

    Com `chave_do_chat`, usa só `GOOGLE_API_KEY_CHAT` (a cota do chat fica separada da coleta); se
    ela não existir, lança `ChaveDoChatAusente`, nunca cai em `GOOGLE_API_KEY` (FR-028)."""
    provedor = nome.split(":", 1)[0]
    argumentos: dict[str, Any] = {"temperature": 0}
    if provedor == "google_genai":
        argumentos["timeout"] = TEMPO_LIMITE_SEGUNDOS
        chave = configuracoes.google_api_key_chat if chave_do_chat else configuracoes.google_api_key
        if chave_do_chat and chave is None:
            raise ChaveDoChatAusente(
                "GOOGLE_API_KEY_CHAT não definida: o chat tem chave própria e nunca usa a da coleta"
            )
        if chave is not None:
            argumentos["api_key"] = chave.get_secret_value()
    elif provedor == "ollama":
        argumentos["base_url"] = configuracoes.ollama_base_url
    return argumentos
