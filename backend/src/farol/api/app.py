"""Fábrica do app FastAPI.

Princípios (constituição): a API devolve JSON, e a única rota que não é de leitura é a pergunta
do chat (`POST /chat`, que responde em fluxo de eventos); o CORS aceita só as origens configuradas,
e o POST só na rota do chat; a documentação interativa (/docs e /redoc) só existe em
desenvolvimento, por variável de ambiente.

Camadas de middleware, de fora para dentro: CORS (por rota), IP real (atrás do proxy), limite de
pedidos, compressão e cache de leitura. O 429 do limite sai com os cabeçalhos do CORS; o cache
guarda o corpo sem comprimir; o fluxo do chat não é comprimido (`text/event-stream`) nem guardado.
"""

import os
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic.json_schema import models_json_schema
from starlette.exceptions import HTTPException as StarletteHTTPException

from farol.api.cache import CacheDeLeitura, VersaoMemorizada
from farol.api.chat import CorsPorRota
from farol.api.dependencias import sessao_da_requisicao
from farol.api.dtos import Erro, ErroDoChat, EventoErro, EventoProgresso, EventoResposta
from farol.api.ip_real import IpReal
from farol.api.limite import LimiteDePedidos
from farol.api.rotas import chat, mapa, paises, saude, vistos
from farol.infra import (
    Configuracoes,
    configurar_logs,
    ler_versao_dos_dados,
    obter_configuracoes,
    obter_logger,
)

PREFIXO = "/api/v1"

__all__ = ["criar_app", "sessao_da_requisicao"]

_log = obter_logger("farol.api")

_RASTREAMENTO_EXTERNO = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")


def criar_app(
    configuracoes: Configuracoes | None = None,
    *,
    relogio_monotonico: Callable[[], float] = time.monotonic,
) -> FastAPI:
    config = configuracoes or obter_configuracoes()
    # Rastreamento externo (LangSmith/LangChain) sempre desligado, mesmo se o ambiente trouxer true:
    # nada da conversa do chat sai para terceiros
    for variavel in _RASTREAMENTO_EXTERNO:
        os.environ[variavel] = "false"
    configurar_logs()
    docs = config.api_docs_habilitada
    app = FastAPI(
        title="Farol Atlas API",
        version="1.2.0",
        description=(
            "Dados do mapa de alertas de viagem do Itamaraty para brasileiros, e um chat que"
            " responde só com base nesses dados. Serviço não oficial."
        ),
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url=f"{PREFIXO}/openapi.json",
    )
    app.state.configuracoes = config

    def ler_versao() -> int:
        # Usa a mesma fonte de sessão das rotas (os testes a trocam por uma sessão deles)
        fornecer = app.dependency_overrides.get(sessao_da_requisicao, sessao_da_requisicao)
        sessoes = fornecer()
        try:
            return ler_versao_dos_dados(next(sessoes))
        finally:
            sessoes.close()

    # Do mais interno ao mais externo (o último adicionado é o primeiro a ver o pedido)
    if config.cache_ttl_segundos > 0:
        app.add_middleware(
            CacheDeLeitura,
            versao=VersaoMemorizada(ler_versao, config.cache_versao_segundos, relogio_monotonico),
            ttl=config.cache_ttl_segundos,
            max_age_do_navegador=config.cache_max_age_navegador_segundos,
            relogio=relogio_monotonico,
        )
    # O /mapa tem cerca de 90 KB de JSON: comprimido, chega bem mais rápido em rede de celular.
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if config.limite_pedidos_por_minuto > 0:
        app.add_middleware(
            LimiteDePedidos,
            por_minuto=config.limite_pedidos_por_minuto,
            rajada=config.limite_rajada,
            relogio=relogio_monotonico,
        )
    app.add_middleware(IpReal, redes_confiaveis=config.redes_confiaveis)
    app.add_middleware(CorsPorRota, origens=config.cors_origens)

    @app.exception_handler(chat.ChatDesligado)
    async def chat_desligado(_: Request, __: chat.ChatDesligado) -> JSONResponse:
        return chat.resposta_do_chat_desligado()

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        return JSONResponse({"detalhe": str(erro.detail)}, status_code=erro.status_code)

    @app.exception_handler(RequestValidationError)
    async def erro_de_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        campos = ", ".join(".".join(str(parte) for parte in e["loc"]) for e in erro.errors())
        return JSONResponse({"detalhe": f"Requisição inválida: {campos}"}, status_code=422)

    @app.exception_handler(Exception)
    async def erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
        if isinstance(erro, HTTPException):  # já tratado acima
            raise erro
        _log.error("erro inesperado na API", exc_info=erro)
        return JSONResponse({"detalhe": "Erro interno"}, status_code=500)

    app.include_router(mapa.roteador, prefix=PREFIXO)
    app.include_router(paises.roteador, prefix=PREFIXO)
    app.include_router(vistos.roteador, prefix=PREFIXO)
    app.include_router(saude.roteador, prefix=PREFIXO)
    app.include_router(chat.roteador, prefix=PREFIXO)
    _publicar_os_eventos_do_chat(app)
    return app


def _publicar_os_eventos_do_chat(app: FastAPI) -> None:
    """Acrescenta ao OpenAPI os esquemas dos eventos do fluxo do chat e dos erros dele.

    O FastAPI descreve o `data` de cada evento só como texto; o contrato v1.2 traz os esquemas
    `EventoProgresso`, `EventoResposta` e `EventoErro` em `components`, e os erros antes do fluxo
    (`ErroDoChat`, `Erro`) são citados por referência.
    """
    gerar = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            esquema = gerar()
            _, definicoes = models_json_schema(
                [
                    (m, "serialization")
                    for m in (EventoProgresso, EventoResposta, EventoErro, ErroDoChat, Erro)
                ],
                ref_template="#/components/schemas/{model}",
            )
            componentes = esquema.setdefault("components", {}).setdefault("schemas", {})
            for nome, definicao in definicoes.get("$defs", {}).items():
                componentes.setdefault(nome, definicao)
        return app.openapi_schema or {}

    app.openapi = openapi  # type: ignore[method-assign]
