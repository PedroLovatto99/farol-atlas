"""Rastreamento externo (LangSmith/LangChain) desligado: nada da conversa sai para terceiros."""

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from farol.api.app import criar_app
from farol.infra import Configuracoes

RAIZ = Path(__file__).resolve().parents[4]
VARIAVEIS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")
URL = "postgresql+psycopg://farol:farol@postgres:5432/farol"


def _servicos(arquivo: str) -> dict[str, dict[str, Any]]:
    conteudo = yaml.safe_load((RAIZ / arquivo).read_text(encoding="utf-8"))
    servicos: dict[str, dict[str, Any]] = conteudo["services"]
    return servicos


@pytest.mark.parametrize("arquivo", ["docker-compose.yml", "docker-compose.prod.yml"])
@pytest.mark.parametrize("servico", ["api", "worker"])
@pytest.mark.parametrize("variavel", VARIAVEIS)
def test_compose_fixa_o_rastreamento_em_false(arquivo: str, servico: str, variavel: str) -> None:
    ambiente = _servicos(arquivo)[servico]["environment"]
    assert str(ambiente[variavel]).lower() == "false"


@pytest.mark.parametrize("variavel", VARIAVEIS)
def test_criar_app_forca_o_rastreamento_desligado(
    monkeypatch: pytest.MonkeyPatch, variavel: str
) -> None:
    for nome in VARIAVEIS:
        monkeypatch.setenv(nome, "true")
    criar_app(Configuracoes(_env_file=None, database_url=URL))
    assert os.environ[variavel] == "false"
