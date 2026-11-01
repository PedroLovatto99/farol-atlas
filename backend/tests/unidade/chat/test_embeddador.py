"""`EmbeddadorGoogle`: tipo de tarefa, dimensão e chave do chat. Sem rede: o cliente é falso."""

from typing import Any

import pytest

from farol.chat import EmbeddadorGoogle, criar_embeddador
from farol.chat.protocolos import Embeddador
from farol.infra import ChaveDoChatAusente, Configuracoes

URL = "postgresql+psycopg://farol:farol@postgres:5432/farol"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in ("GOOGLE_API_KEY", "GOOGLE_API_KEY_CHAT", "EMBEDDINGS_MODELO"):
        monkeypatch.delenv(nome, raising=False)


def configuracoes(**campos: Any) -> Configuracoes:
    return Configuracoes(_env_file=None, database_url=URL, **campos)


class ClienteFalso:
    """Faz o papel de `GoogleGenerativeAIEmbeddings`: guarda como foi chamado."""

    def __init__(self, **argumentos: Any) -> None:
        self.argumentos = argumentos
        self.chamadas: list[tuple[str, Any, dict[str, Any]]] = []

    def embed_documents(self, textos: list[str], **extra: Any) -> list[list[float]]:
        self.chamadas.append(("documentos", textos, extra))
        return [[float(len(t)), 0.0] for t in textos]

    def embed_query(self, texto: str, **extra: Any) -> list[float]:
        self.chamadas.append(("pergunta", texto, extra))
        return [float(len(texto)), 1.0]


def test_trechos_usam_tarefa_de_documento_e_a_dimensao_configurada() -> None:
    cliente = ClienteFalso()
    embeddador = EmbeddadorGoogle(cliente, modelo="google_genai:gemini-embedding-001", dimensoes=2)

    vetores = embeddador.vetorizar_documentos(["um", "dois"])

    assert vetores == [[2.0, 0.0], [4.0, 0.0]]
    assert cliente.chamadas == [
        (
            "documentos",
            ["um", "dois"],
            {"task_type": "RETRIEVAL_DOCUMENT", "output_dimensionality": 2},
        )
    ]


def test_a_pergunta_usa_tarefa_de_consulta() -> None:
    cliente = ClienteFalso()
    embeddador = EmbeddadorGoogle(cliente, modelo="google_genai:gemini-embedding-001", dimensoes=2)

    assert embeddador.vetorizar_pergunta("e o visto?") == [10.0, 1.0]
    assert cliente.chamadas == [
        ("pergunta", "e o visto?", {"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 2})
    ]


def test_lista_vazia_nao_chama_o_servico() -> None:
    cliente = ClienteFalso()
    embeddador = EmbeddadorGoogle(cliente, modelo="m", dimensoes=2)
    assert embeddador.vetorizar_documentos([]) == []
    assert cliente.chamadas == []


def test_expoe_o_modelo_e_a_dimensao_que_o_indice_grava() -> None:
    embeddador = EmbeddadorGoogle(
        ClienteFalso(), modelo="google_genai:gemini-embedding-001", dimensoes=768
    )
    assert (embeddador.modelo, embeddador.dimensoes) == ("google_genai:gemini-embedding-001", 768)
    assert isinstance(embeddador, Embeddador)


def test_criar_usa_a_chave_do_chat_e_o_modelo_das_configuracoes() -> None:
    criados: list[ClienteFalso] = []

    def fabrica(**argumentos: Any) -> ClienteFalso:
        criados.append(ClienteFalso(**argumentos))
        return criados[-1]

    embeddador = criar_embeddador(
        configuracoes(
            google_api_key="chave-da-coleta",
            google_api_key_chat="chave-do-chat",
            embeddings_dimensoes=256,
        ),
        fabrica=fabrica,
    )

    assert criados[0].argumentos == {
        "model": "gemini-embedding-001",
        "google_api_key": "chave-do-chat",
    }
    assert (embeddador.modelo, embeddador.dimensoes) == ("google_genai:gemini-embedding-001", 256)


def test_sem_chave_do_chat_falha_mesmo_com_a_chave_da_coleta() -> None:
    with pytest.raises(ChaveDoChatAusente):
        criar_embeddador(configuracoes(google_api_key="chave-da-coleta"), fabrica=ClienteFalso)


def test_so_o_google_e_aceito() -> None:
    with pytest.raises(ValueError, match="google_genai"):
        criar_embeddador(
            configuracoes(google_api_key_chat="k", embeddings_modelo="ollama:nomic-embed-text"),
            fabrica=ClienteFalso,
        )


def test_a_chave_nao_aparece_no_repr() -> None:
    embeddador = criar_embeddador(
        configuracoes(google_api_key_chat="segredo-do-chat"), fabrica=ClienteFalso
    )
    assert "segredo-do-chat" not in repr(embeddador)
