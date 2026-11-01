"""Embeddings do Google para o índice de trechos (`Embeddador`, em `protocolos`).

Usa a chave do chat (`GOOGLE_API_KEY_CHAT`, projeto separado do da coleta) e nunca cai na da coleta.
O trecho vai como `RETRIEVAL_DOCUMENT` e a pergunta como `RETRIEVAL_QUERY`, com a dimensão das
configurações. Só o texto do trecho ou da pergunta sai daqui; a chave não vai a log nem a `repr`.
"""

from collections.abc import Callable, Sequence
from typing import Any, Protocol

from farol.infra import ChaveDoChatAusente, Configuracoes

TAREFA_DO_TRECHO = "RETRIEVAL_DOCUMENT"
TAREFA_DA_PERGUNTA = "RETRIEVAL_QUERY"


class ClienteDeEmbeddings(Protocol):
    """O que o `GoogleGenerativeAIEmbeddings` do LangChain oferece e o embeddador usa."""

    def embed_documents(self, texts: list[str], **extra: Any) -> list[list[float]]: ...

    def embed_query(self, text: str, **extra: Any) -> list[float]: ...


class EmbeddadorGoogle:
    def __init__(self, cliente: Any, *, modelo: str, dimensoes: int) -> None:
        self._cliente = cliente
        self.modelo = modelo
        self.dimensoes = dimensoes

    def __repr__(self) -> str:
        return f"EmbeddadorGoogle(modelo={self.modelo!r}, dimensoes={self.dimensoes})"

    def vetorizar_documentos(self, textos: Sequence[str]) -> list[Sequence[float]]:
        if not textos:
            return []
        vetores = self._cliente.embed_documents(
            list(textos), task_type=TAREFA_DO_TRECHO, output_dimensionality=self.dimensoes
        )
        return [list(vetor) for vetor in vetores]

    def vetorizar_pergunta(self, texto: str) -> Sequence[float]:
        vetor = self._cliente.embed_query(
            texto, task_type=TAREFA_DA_PERGUNTA, output_dimensionality=self.dimensoes
        )
        return list(vetor)


def _fabrica_padrao(**argumentos: Any) -> Any:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(**argumentos)


def criar_embeddador(
    configuracoes: Configuracoes, *, fabrica: Callable[..., Any] = _fabrica_padrao
) -> EmbeddadorGoogle:
    """O embeddador de `EMBEDDINGS_MODELO` ("google_genai:modelo") com a chave do chat.

    Lança `ChaveDoChatAusente` sem `GOOGLE_API_KEY_CHAT` e `ValueError` para outro provedor.
    """
    nome = configuracoes.embeddings_modelo
    provedor, _, modelo = nome.partition(":")
    if provedor != "google_genai" or not modelo:
        raise ValueError(f"EMBEDDINGS_MODELO deve ser 'google_genai:<modelo>', e veio {nome!r}")
    chave = configuracoes.google_api_key_chat
    if chave is None:
        raise ChaveDoChatAusente(
            "GOOGLE_API_KEY_CHAT não definida: o chat tem chave própria e nunca usa a da coleta"
        )
    cliente = fabrica(model=modelo, google_api_key=chave.get_secret_value())
    return EmbeddadorGoogle(cliente, modelo=nome, dimensoes=configuracoes.embeddings_dimensoes)
