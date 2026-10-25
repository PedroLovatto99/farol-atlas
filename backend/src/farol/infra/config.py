"""Configuração do sistema, lida de variáveis de ambiente (pydantic-settings).

Chaves e senhas ficam só em variáveis de ambiente do servidor, nunca no repositório nem no
frontend (constituição, princípio VIII). Por isso os segredos são `SecretStr`: não aparecem em
`repr`, `str` nem em logs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Banco de dados
    database_url: SecretStr
    database_url_teste: SecretStr | None = None

    # API
    cors_origens: Annotated[list[str], NoDecode] = []
    api_docs_habilitada: bool = False  # /docs e /redoc: só em desenvolvimento

    # Coleta (worker)
    contato_coleta: str | None = None  # vai no User-Agent
    pausa_segundos: float = 2.0
    limite_horas_partida: int = 20

    # Classificador de alertas (LLM)
    llm_classificador: str = "google_genai:gemini-3.6-flash"
    google_api_key: SecretStr | None = None
    ollama_base_url: str = "http://host.docker.internal:11434"

    # Pasta com os dados de seed (postos, territórios). Local: ../dados; no Docker: /app/dados
    diretorio_dados: Path = Path("../dados")

    @field_validator("cors_origens", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
