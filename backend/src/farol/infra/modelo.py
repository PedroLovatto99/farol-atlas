"""Argumentos de criação do modelo de LLM, a partir de "provedor:modelo".

Fica na infra para o classificador e o tradutor montarem o modelo do mesmo jeito. Não importa
LangChain: quem cria o modelo (`init_chat_model`) é cada módulo.
"""

from typing import Any

from farol.infra.config import Configuracoes

TEMPO_LIMITE_SEGUNDOS = 90


def argumentos_do_modelo(nome: str, configuracoes: Configuracoes) -> dict[str, Any]:
    """Argumentos de `init_chat_model` para o modelo `nome` ("provedor:modelo"), temperatura 0."""
    provedor = nome.split(":", 1)[0]
    argumentos: dict[str, Any] = {"temperature": 0}
    if provedor == "google_genai":
        argumentos["timeout"] = TEMPO_LIMITE_SEGUNDOS
        if configuracoes.google_api_key is not None:
            argumentos["api_key"] = configuracoes.google_api_key.get_secret_value()
    elif provedor == "ollama":
        argumentos["base_url"] = configuracoes.ollama_base_url
    return argumentos
