"""Fábrica do app FastAPI.

Princípios (constituição): a API só devolve JSON; as rotas públicas são de leitura, menos o chat,
que responde sem gravar nada; o CORS aceita só as origens configuradas; a documentação interativa
(/docs e /redoc) só existe em desenvolvimento, por variável de ambiente.

Camadas de middleware, de fora para dentro: CORS, IP real (atrás do proxy), limite de pedidos,
compressão e cache de leitura. O 429 do limite sai com os cabeçalhos do CORS; o cache guarda o corpo
sem comprimir.
"""

import time
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from farol.api.cache import CacheDeLeitura, VersaoMemorizada
from farol.api.dependencias import sessao_da_requisicao
from farol.api.ip_real import IpReal
from farol.api.limite import BaldeDeFichas, LimiteDePedidos
from farol.api.rotas import chat, mapa, paises, saude, vistos
from farol.chat import criar_modelo_do_chat
from farol.infra import (
    Configuracoes,
    configurar_logs,
    ler_versao_dos_dados,
    obter_configuracoes,
    obter_logger,
)

PREFIXO = "/api/v1"
CAMINHO_DO_CHAT = f"{PREFIXO}/chat"

__all__ = ["criar_app", "sessao_da_requisicao"]

_log = obter_logger("farol.api")


class CorsPorCaminho:
    """Dois CORS sobre o mesmo app: POST e `Content-Type` só no chat; o resto, só GET (D7)."""

    def __init__(self, app: ASGIApp, *, origens: list[str]) -> None:
        self._leitura = CORSMiddleware(
            app,
            allow_origins=origens,
            allow_methods=["GET"],
            allow_headers=[],
            allow_credentials=False,
        )
        self._chat = CORSMiddleware(
            app,
            allow_origins=origens,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
            allow_credentials=False,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        eh_chat = scope["type"] == "http" and scope["path"] == CAMINHO_DO_CHAT
        await (self._chat if eh_chat else self._leitura)(scope, receive, send)


def criar_app(
    configuracoes: Configuracoes | None = None,
    *,
    relogio_monotonico: Callable[[], float] = time.monotonic,
) -> FastAPI:
    config = configuracoes or obter_configuracoes()
    configurar_logs()
    docs = config.api_docs_habilitada
    app = FastAPI(
        title="Farol Atlas API",
        version="1.2.0",
        description=(
            "Mapa de alertas de viagem do Itamaraty e requisitos de visto para brasileiros."
            " Serviço não oficial."
        ),
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url=f"{PREFIXO}/openapi.json",
    )

    perguntas_por_hora = config.chat_perguntas_por_hora
    app.state.chat_perguntas_por_hora = perguntas_por_hora
    app.state.balde_do_chat = BaldeDeFichas(
        por_minuto=perguntas_por_hora / 60, rajada=perguntas_por_hora, relogio=relogio_monotonico
    )
    app.state.modelo_do_chat = criar_modelo_do_chat(config)

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
    app.add_middleware(CorsPorCaminho, origens=config.cors_origens)

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_: Request, erro: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            {"detalhe": str(erro.detail)}, status_code=erro.status_code, headers=erro.headers
        )

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
    app.include_router(chat.roteador, prefix=PREFIXO)
    app.include_router(saude.roteador, prefix=PREFIXO)
    return app
