"""Argumentos do modelo de LLM: montados na infra, sem importar LangChain."""

import ast
from pathlib import Path
from typing import Any

import pytest

from farol.infra import Configuracoes, argumentos_do_modelo
from farol.infra import modelo as modulo_modelo

URL = "postgresql+psycopg://farol:farol@postgres:5432/farol"


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch: pytest.MonkeyPatch) -> None:
    for nome in ("GOOGLE_API_KEY", "OLLAMA_BASE_URL", "LLM_CLASSIFICADOR", "LLM_TRADUTOR"):
        monkeypatch.delenv(nome, raising=False)


def configuracoes(**campos: Any) -> Configuracoes:
    return Configuracoes(_env_file=None, database_url=URL, **campos)


def test_google_usa_temperatura_zero_tempo_limite_e_chave() -> None:
    argumentos = argumentos_do_modelo(
        "google_genai:gemini-3.6-flash", configuracoes(google_api_key="chave-de-teste")
    )
    assert argumentos == {"temperature": 0, "timeout": 90, "api_key": "chave-de-teste"}


def test_google_sem_chave_nao_leva_api_key() -> None:
    argumentos = argumentos_do_modelo("google_genai:gemini-3.6-flash", configuracoes())
    assert argumentos == {"temperature": 0, "timeout": 90}


def test_ollama_usa_a_url_base() -> None:
    argumentos = argumentos_do_modelo(
        "ollama:llama3", configuracoes(ollama_base_url="http://ollama:11434")
    )
    assert argumentos == {"temperature": 0, "base_url": "http://ollama:11434"}


def test_outro_provedor_so_leva_a_temperatura() -> None:
    argumentos = argumentos_do_modelo("outro:modelo-x", configuracoes(google_api_key="chave"))
    assert argumentos == {"temperature": 0}


def test_o_modulo_nao_importa_langchain() -> None:
    arvore = ast.parse(Path(modulo_modelo.__file__).read_text(encoding="utf-8"))
    importados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module is not None:
            importados.add(no.module)
    assert not [nome for nome in importados if nome.split(".")[0].startswith("langchain")]
