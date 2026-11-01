"""CORS por rota (contracts/caddy-cors-limites.md, seção 2).

A pergunta do chat é a única escrita da API: `POST /api/v1/chat` aceita `Content-Type` e expõe o
`Retry-After` (o navegador precisa lê-lo no 429). Todo o resto continua só com GET e sem cabeçalho
nenhum. As origens, nos dois casos, são as de `CORS_ORIGENS`, sem credenciais.
"""

from collections.abc import Sequence

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

CAMINHO_DO_CHAT = "/api/v1/chat"


class CorsPorRota:
    def __init__(self, app: ASGIApp, *, origens: Sequence[str]) -> None:
        self._leitura = CORSMiddleware(
            app,
            allow_origins=list(origens),
            allow_methods=["GET"],
            allow_headers=[],
            allow_credentials=False,
        )
        self._chat = CORSMiddleware(
            app,
            allow_origins=list(origens),
            allow_methods=["POST"],
            allow_headers=["Content-Type"],
            expose_headers=["Retry-After"],
            allow_credentials=False,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == CAMINHO_DO_CHAT:
            await self._chat(scope, receive, send)
        else:
            await self._leitura(scope, receive, send)
