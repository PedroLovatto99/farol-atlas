"""IP real do visitante atrás do proxy reverso (Caddy).

A API só lê o `X-Forwarded-For` quando o pedido chegou DIRETO de uma rede confiável (a rede interna
do Docker onde está o Caddy). De qualquer outro endereço o cabeçalho é ignorado: sem isso, qualquer
visitante forjaria o próprio IP e escaparia do limite de pedidos.

Na cadeia do cabeçalho, anda-se da direita para a esquerda pulando os endereços confiáveis; o
primeiro que não é confiável é o visitante. O que está à esquerda disso pode ter sido forjado.
"""

import ipaddress
from collections.abc import Sequence

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

Rede = ipaddress.IPv4Network | ipaddress.IPv6Network
Endereco = ipaddress.IPv4Address | ipaddress.IPv6Address


def _endereco(texto: str) -> Endereco | None:
    try:
        return ipaddress.ip_address(texto.strip())
    except ValueError:
        return None


def _confiavel(endereco: Endereco, redes: Sequence[Rede]) -> bool:
    return any(endereco in rede for rede in redes if rede.version == endereco.version)


def ip_do_visitante(par: str | None, encaminhado: str | None, redes: Sequence[Rede]) -> str | None:
    """O IP do visitante, dado o par da conexão e o X-Forwarded-For; `par` se não houver como."""
    origem = _endereco(par) if par else None
    if origem is None or not redes or not _confiavel(origem, redes) or not encaminhado:
        return par
    cadeia = [_endereco(parte) for parte in encaminhado.split(",")]
    for endereco in reversed(cadeia):
        if endereco is None:
            return par  # cabeçalho malformado: não adivinha
        if not _confiavel(endereco, redes):
            return str(endereco)
    return par


class IpReal:
    """Troca o `client` do escopo pelo IP do visitante (quando o pedido veio do proxy)."""

    def __init__(self, app: ASGIApp, redes_confiaveis: Sequence[Rede]) -> None:
        self.app = app
        self._redes = list(redes_confiaveis)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._redes and scope.get("client"):
            par = scope["client"][0]
            encaminhado = Headers(scope=scope).get("x-forwarded-for")
            ip = ip_do_visitante(par, encaminhado, self._redes)
            if ip is not None and ip != par:
                scope = {**scope, "client": (ip, 0)}
        await self.app(scope, receive, send)
