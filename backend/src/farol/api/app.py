"""Fábrica do app FastAPI.

Princípios (constituição): a API só devolve JSON; todas as rotas públicas são de leitura; o CORS
aceita só as origens configuradas; a documentação interativa (/docs e /redoc) só existe em
desenvolvimento, por variável de ambiente.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from farol.api.dependencias import sessao_da_requisicao
from farol.api.rotas import mapa, saude
from farol.infra import Configuracoes, configurar_logs, obter_configuracoes, obter_logger

PREFIXO = "/api/v1"

__all__ = ["criar_app", "sessao_da_requisicao"]

_log = obter_logger("farol.api")


def criar_app(configuracoes: Configuracoes | None = None) -> FastAPI:
    config = configuracoes or obter_configuracoes()
    configurar_logs()
    docs = config.api_docs_habilitada
    app = FastAPI(
        title="Farol Atlas API",
        version="1.0.0",
        description="Mapa de alertas de viagem do Itamaraty para brasileiros. Serviço não oficial.",
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url=f"{PREFIXO}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origens,
        allow_methods=["GET"],
        allow_headers=[],
        allow_credentials=False,
    )

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
    app.include_router(saude.roteador, prefix=PREFIXO)
    return app
