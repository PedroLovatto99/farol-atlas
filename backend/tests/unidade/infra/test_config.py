"""Configuração por variáveis de ambiente (pydantic-settings)."""

import pytest
from pydantic import ValidationError

from farol.infra import Configuracoes

URL = "postgresql+psycopg://farol:senha-secreta@postgres:5432/farol"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove do ambiente tudo o que a configuração lê, para cada teste começar do zero."""
    for nome in (
        "DATABASE_URL",
        "DATABASE_URL_TESTE",
        "CORS_ORIGENS",
        "API_DOCS_HABILITADA",
        "CONTATO_COLETA",
        "PAUSA_SEGUNDOS",
        "LIMITE_HORAS_PARTIDA",
        "LLM_CLASSIFICADOR",
        "LLM_TRADUTOR",
        "GOOGLE_API_KEY",
        "OLLAMA_BASE_URL",
        "DIRETORIO_DADOS",
    ):
        monkeypatch.delenv(nome, raising=False)


def criar() -> Configuracoes:
    """Lê só o ambiente do teste (nada do .env do desenvolvedor)."""
    return Configuracoes(_env_file=None)


def test_database_url_e_obrigatoria() -> None:
    with pytest.raises(ValidationError):
        criar()


def test_cors_origens_vira_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("CORS_ORIGENS", "http://localhost:5173, https://farol.exemplo.com")
    configuracao = criar()
    assert configuracao.cors_origens == ["http://localhost:5173", "https://farol.exemplo.com"]


def test_cors_origens_vazio_nao_aceita_ninguem(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    assert criar().cors_origens == []


def test_docs_da_api_desligadas_por_padrao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    assert criar().api_docs_habilitada is False


def test_docs_da_api_ligadas_por_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("API_DOCS_HABILITADA", "true")
    assert criar().api_docs_habilitada is True


def test_valores_padrao_da_coleta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.pausa_segundos == 2.0
    assert configuracao.limite_horas_partida == 20
    assert configuracao.llm_classificador == "google_genai:gemini-3.6-flash"


def test_segredos_nunca_aparecem_no_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-super-secreta")
    configuracao = criar()
    texto = f"{configuracao!r} {configuracao!s}"
    assert "senha-secreta" not in texto
    assert "chave-super-secreta" not in texto
    assert configuracao.database_url.get_secret_value() == URL


def test_tradutor_sem_variavel_usa_o_modelo_do_classificador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    configuracao = criar()
    assert configuracao.llm_tradutor == configuracao.llm_classificador

    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    assert criar().llm_tradutor == "ollama:llama3"


def test_tradutor_vazio_no_env_tambem_usa_o_do_classificador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    monkeypatch.setenv("LLM_TRADUTOR", "   ")
    assert criar().llm_tradutor == "ollama:llama3"


def test_tradutor_com_variavel_vale_a_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.setenv("LLM_CLASSIFICADOR", "ollama:llama3")
    monkeypatch.setenv("LLM_TRADUTOR", "google_genai:gemini-3.6-flash")
    configuracao = criar()
    assert configuracao.llm_tradutor == "google_genai:gemini-3.6-flash"
    assert configuracao.llm_classificador == "ollama:llama3"
