"""Limite de pedidos por IP: balde de fichas em memória.

Cada IP tem um balde com `rajada` fichas, que enchem a `por_minuto / 60` por segundo; cada pedido
gasta uma. Sem ficha, a resposta é 429 com `Retry-After`. O estado fica na memória do processo: com
N processos da API o limite efetivo seria de até N vezes o configurado. Por isso a produção roda um
processo só (veja docs/deploy.md).
"""

import json
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from starlette.types import ASGIApp, Receive, Scope, Send

CAMINHOS_LIVRES = frozenset({"/api/v1/saude"})
LIMPEZA_A_CADA = 1024  # pedidos entre uma limpeza de baldes parados e a seguinte


@dataclass
class _Balde:
    fichas: float
    atualizado_em: float


class BaldeDeFichas:
    def __init__(
        self, por_minuto: int, rajada: int, relogio: Callable[[], float] = time.monotonic
    ) -> None:
        self._por_segundo = por_minuto / 60
        self._rajada = rajada
        self._relogio = relogio
        self._baldes: dict[str, _Balde] = {}
        self._trava = threading.Lock()
        self._pedidos = 0

    def tentar(self, chave: str) -> int | None:
        """Gasta uma ficha. Devolve None se passou, ou os segundos até haver ficha."""
        agora = self._relogio()
        with self._trava:
            self._pedidos += 1
            if self._pedidos % LIMPEZA_A_CADA == 0:
                self._limpar(agora)
            balde = self._baldes.get(chave)
            if balde is None:
                balde = _Balde(fichas=float(self._rajada), atualizado_em=agora)
                self._baldes[chave] = balde
            else:
                decorrido = max(0.0, agora - balde.atualizado_em)
                balde.fichas = min(self._rajada, balde.fichas + decorrido * self._por_segundo)
                balde.atualizado_em = agora
            if balde.fichas >= 1:
                balde.fichas -= 1
                return None
            return max(1, math.ceil((1 - balde.fichas) / self._por_segundo))

    def _limpar(self, agora: float) -> None:
        """Descarta os baldes que já estariam cheios: esquecê-los não muda nada."""
        cheio_em = self._rajada / self._por_segundo
        parados = [k for k, b in self._baldes.items() if agora - b.atualizado_em >= cheio_em]
        for chave in parados:
            del self._baldes[chave]

    @property
    def tamanho(self) -> int:
        return len(self._baldes)


class LimiteDePedidos:
    """Middleware ASGI. Fica depois do `IpReal`: a chave é o IP que o escopo já traz."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        por_minuto: int,
        rajada: int,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self._balde = BaldeDeFichas(por_minuto, rajada, relogio)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in CAMINHOS_LIVRES:
            await self.app(scope, receive, send)
            return
        cliente = scope.get("client")
        espera = self._balde.tentar(cliente[0] if cliente else "desconhecido")
        if espera is None:
            await self.app(scope, receive, send)
            return
        corpo = json.dumps(
            {"detalhe": f"Muitos pedidos. Tente de novo em {espera} s."}, ensure_ascii=False
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(corpo)).encode()),
                    (b"retry-after", str(espera).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": corpo})
