"""Configuração do sistema, lida de variáveis de ambiente (pydantic-settings).

Chaves e senhas ficam só em variáveis de ambiente do servidor, nunca no repositório nem no
frontend (constituição, princípio VIII). Por isso os segredos são `SecretStr`: não aparecem em
`repr`, `str` nem em logs.
"""

import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # "producao" liga as exigências de partida (CORS, proxy confiável e coletas definidos)
    ambiente: Literal["desenvolvimento", "producao"] = "desenvolvimento"

    # Banco de dados
    database_url: SecretStr
    database_url_teste: SecretStr | None = None

    # API
    cors_origens: Annotated[list[str], NoDecode] = []
    api_docs_habilitada: bool = False  # /docs e /redoc: só em desenvolvimento
    # Redes (CIDR, separadas por vírgula) de onde o proxy reverso fala com a API. Só dos pedidos
    # que vêm delas a API aceita o X-Forwarded-For; vazio = nunca confia (acesso direto).
    proxy_confiavel: Annotated[list[str], NoDecode] = []
    # Limite de pedidos por IP: média por minuto e rajada (balde de fichas); 0 desliga
    limite_pedidos_por_minuto: int = Field(120, ge=0)
    limite_rajada: int = Field(40, ge=1)
    # Cache em memória das respostas de leitura; 0 desliga. A versão dos dados (contador que sobe
    # a cada escrita) é consultada no máximo uma vez por `cache_versao_segundos`
    cache_ttl_segundos: int = Field(300, ge=0)
    cache_versao_segundos: int = Field(15, ge=0)
    cache_max_age_navegador_segundos: int = Field(60, ge=0)  # Cache-Control: max-age

    # Coleta (worker)
    contato_coleta: str | None = None  # vai no User-Agent
    pausa_segundos: float = 2.0
    limite_horas_partida: int = 20
    # Liga as coletas agendadas e as da partida. Indefinida = desligadas; em produção é obrigatória.
    coletas_automaticas: bool | None = None
    # Pasta do arquivo de log do worker (rotativo); vazio = só a saída padrão
    diretorio_logs: str = ""

    # Classificador de alertas (LLM)
    llm_classificador: str = "google_genai:gemini-3.6-flash"
    # Tradutor das observações de visto; vazio = o mesmo modelo do classificador
    llm_tradutor: str = ""
    google_api_key: SecretStr | None = None
    ollama_base_url: str = "http://host.docker.internal:11434"

    # Chat de dúvidas de viagem. Só liga por decisão explícita; em produção, com limites positivos
    chat_habilitado: bool = False
    llm_chat: str = ""  # vazio = o mesmo modelo do classificador
    llm_chat_alternativo: str = ""  # vazio = sem plano B
    google_api_key_chat: SecretStr | None = (
        None  # obrigatória com o chat ligado; nunca cai em google_api_key
    )
    embeddings_modelo: str = "google_genai:gemini-embedding-001"
    embeddings_dimensoes: int = Field(768, ge=1)
    chat_limite_por_hora_por_ip: int = 20
    chat_limite_por_dia: int = 500
    chat_tempo_maximo_segundos: int = Field(20, ge=1)
    chat_pergunta_max_caracteres: int = Field(500, ge=1)
    chat_historico_mensagens: int = Field(6, ge=0)
    chat_trechos_por_pergunta: int = Field(4, ge=1)
    indexacao_intervalo_minutos: int = Field(5, ge=1)

    # Pasta com os dados de seed (postos, territórios). Local: ../dados; no Docker: /app/dados
    diretorio_dados: Path = Path("../dados")

    @field_validator("cors_origens", mode="before")
    @classmethod
    def _separar_origens(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [origem.strip() for origem in valor.split(",") if origem.strip()]
        return valor

    @field_validator("proxy_confiavel", mode="before")
    @classmethod
    def _separar_redes(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [rede.strip() for rede in valor.split(",") if rede.strip()]
        return valor

    @field_validator("proxy_confiavel")
    @classmethod
    def _redes_validas(cls, valor: list[str]) -> list[str]:
        for rede in valor:
            try:
                ipaddress.ip_network(rede, strict=False)
            except ValueError as erro:
                raise ValueError(f"rede inválida em PROXY_CONFIAVEL: {rede!r}") from erro
        return valor

    @property
    def redes_confiaveis(self) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        return [ipaddress.ip_network(rede, strict=False) for rede in self.proxy_confiavel]

    @property
    def coletas_ligadas(self) -> bool:
        return self.coletas_automaticas is True

    @property
    def problema_da_chave_do_chat(self) -> str | None:
        """Por que o chat ligado não tem como falar com o provedor, ou nulo se está tudo certo.

        Ele usa modelos do Google e a chave dele é só `GOOGLE_API_KEY_CHAT`, nunca a da coleta
        (FR-028)."""
        modelos = (
            self.llm_chat or self.llm_classificador,
            self.llm_chat_alternativo,
            self.embeddings_modelo,
        )
        usa_google = any(m.startswith("google_genai:") for m in modelos)
        if usa_google and self.google_api_key_chat is None:
            return (
                "GOOGLE_API_KEY_CHAT não definida: o chat usa modelos do Google e tem chave "
                "própria (nunca usa GOOGLE_API_KEY, que é da coleta)"
            )
        return None

    @property
    def motivo_chat_indisponivel(self) -> str | None:
        """Nulo se o chat está ligado e pronto; senão, o motivo (para o log e para o aviso)."""
        if not self.chat_habilitado:
            return "CHAT_HABILITADO não está ligado"
        return self.problema_da_chave_do_chat

    @property
    def chat_disponivel(self) -> bool:
        return self.motivo_chat_indisponivel is None

    @model_validator(mode="after")
    def _exigencias_de_producao(self) -> Self:
        if self.ambiente != "producao":
            return self
        problemas: list[str] = []
        if not self.cors_origens or any(
            not origem.startswith("https://") or "*" in origem for origem in self.cors_origens
        ):
            problemas.append("CORS_ORIGENS deve listar origens https:// (sem curinga)")
        if not self.proxy_confiavel:
            problemas.append("PROXY_CONFIAVEL deve ter a rede do proxy reverso")
        if self.coletas_automaticas is None:
            problemas.append("COLETAS_AUTOMATICAS deve ser definida (true ou false)")
        if self.chat_habilitado:
            if self.chat_limite_por_hora_por_ip <= 0:
                problemas.append("CHAT_LIMITE_POR_HORA_POR_IP deve ser maior que zero")
            if self.chat_limite_por_dia <= 0:
                problemas.append("CHAT_LIMITE_POR_DIA deve ser maior que zero")
            if (problema := self.problema_da_chave_do_chat) is not None:
                problemas.append(problema)
        if problemas:
            raise ValueError("configuração de produção incompleta: " + "; ".join(problemas))
        return self

    @model_validator(mode="after")
    def _tradutor_padrao(self) -> Self:
        self.llm_tradutor = self.llm_tradutor.strip() or self.llm_classificador
        self.llm_chat = self.llm_chat.strip() or self.llm_classificador
        self.llm_chat_alternativo = self.llm_chat_alternativo.strip()
        return self


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
