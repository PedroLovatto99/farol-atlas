"""Cache em memória das respostas de leitura (/mapa, /paises/{codigo}, /vistos).

Estratégia: cada resposta guardada leva a "versão dos dados" do momento (um contador no banco que
sobe a cada escrita; veja `farol.infra.versao`). Num pedido, se a versão atual for a mesma e a
entrada tiver menos de `ttl` segundos, devolve a guardada; senão, refaz. A versão atual é consultada
no máximo uma vez a cada `intervalo` segundos, então depois de uma coleta, classificação ou comando
do dono nenhum visitante recebe dado antigo por mais que esse intervalo (15 s). O `ttl` (5 min) é só
o teto para o que muda sem escrita, como o "desatualizado", que depende da hora.

Só guarda respostas 200 de GET. Se a versão não puder ser lida (banco fora do ar), o pedido passa
direto, sem cache. O navegador recebe `Cache-Control: public, max-age=...`; o /saude, `no-store`.
"""

import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ROTAS_EM_CACHE = re.compile(r"^/api/v1/(mapa|vistos|paises/[A-Z]{2,3})$")
ROTA_SEM_CACHE = "/api/v1/saude"
MAXIMO_DE_ENTRADAS = 512

Cabecalhos = list[tuple[bytes, bytes]]


@dataclass(frozen=True)
class _Entrada:
    versao: int
    guardada_em: float
    cabecalhos: Cabecalhos
    corpo: bytes


class VersaoMemorizada:
    """Lê a versão dos dados no máximo uma vez a cada `intervalo` segundos (falhas incluídas)."""

    def __init__(
        self,
        ler: Callable[[], int],
        intervalo: float,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ler = ler
        self._intervalo = intervalo
        self._relogio = relogio
        self._valor: int | None = None
        self._lida_em: float | None = None
        self._trava = threading.Lock()

    def obter(self) -> int | None:
        with self._trava:
            agora = self._relogio()
            if self._lida_em is None or agora - self._lida_em >= self._intervalo:
                try:
                    self._valor = self._ler()
                except Exception:  # banco fora do ar: o pedido segue sem cache
                    self._valor = None
                self._lida_em = agora
            return self._valor


def _com_cache_control(cabecalhos: Cabecalhos, valor: bytes) -> Cabecalhos:
    return [*(c for c in cabecalhos if c[0].lower() != b"cache-control"), (b"cache-control", valor)]


class CacheDeLeitura:
    def __init__(
        self,
        app: ASGIApp,
        *,
        versao: VersaoMemorizada,
        ttl: float,
        max_age_do_navegador: int,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self._versao = versao
        self._ttl = ttl
        self._relogio = relogio
        self._navegador = f"public, max-age={max_age_do_navegador}".encode()
        self._entradas: dict[str, _Entrada] = {}
        self._versao_das_entradas: int | None = None
        self._trava = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        caminho = scope["path"]
        if caminho == ROTA_SEM_CACHE:
            await self._sem_cache(scope, receive, send)
            return
        if scope["method"] != "GET" or not ROTAS_EM_CACHE.match(caminho):
            await self.app(scope, receive, send)
            return
        versao = await run_in_threadpool(self._versao.obter)  # consulta o banco, às vezes
        if versao is None:
            await self.app(scope, receive, send)
            return
        chave = f"{caminho}?{scope.get('query_string', b'').decode('latin-1')}"
        entrada = self._buscar(chave, versao)
        if entrada is None:
            await self._produzir(scope, receive, send, chave, versao)
            return
        cabecalhos = _com_cache_control(entrada.cabecalhos, self._navegador)
        await send({"type": "http.response.start", "status": 200, "headers": cabecalhos})
        await send({"type": "http.response.body", "body": entrada.corpo})

    # ------------------------------------------------------------------ guardar e buscar
    def _buscar(self, chave: str, versao: int) -> _Entrada | None:
        with self._trava:
            if self._versao_das_entradas != versao:
                self._entradas.clear()
                self._versao_das_entradas = versao
                return None
            entrada = self._entradas.get(chave)
            if entrada is None or self._relogio() - entrada.guardada_em >= self._ttl:
                return None
            return entrada

    def _guardar(self, chave: str, entrada: _Entrada) -> None:
        with self._trava:
            if entrada.versao != self._versao_das_entradas:
                return  # a versão mudou no meio do pedido: o que foi lido pode ser antigo
            if len(self._entradas) >= MAXIMO_DE_ENTRADAS and chave not in self._entradas:
                del self._entradas[next(iter(self._entradas))]  # a mais antiga
            self._entradas[chave] = entrada

    # ------------------------------------------------------------------ passagem
    async def _sem_cache(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def com_no_store(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                cabecalhos = _com_cache_control(list(mensagem["headers"]), b"no-store")
                mensagem = {**mensagem, "headers": cabecalhos}
            await send(mensagem)

        await self.app(scope, receive, com_no_store)

    async def _produzir(
        self, scope: Scope, receive: Receive, send: Send, chave: str, versao: int
    ) -> None:
        inicio: Message | None = None
        pedacos: list[bytes] = []

        async def capturar(mensagem: Message) -> None:
            nonlocal inicio
            if mensagem["type"] == "http.response.start":
                if mensagem["status"] == 200:
                    inicio = mensagem  # segura até ter o corpo inteiro
                else:
                    await send(mensagem)
                return
            if inicio is None:  # resposta que não é 200: segue sem guardar
                await send(mensagem)
                return
            pedacos.append(mensagem.get("body", b""))
            if mensagem.get("more_body", False):
                return
            corpo = b"".join(pedacos)
            cabecalhos = list(inicio["headers"])
            self._guardar(
                chave,
                _Entrada(
                    versao=versao,
                    guardada_em=self._relogio(),
                    cabecalhos=[c for c in cabecalhos if c[0].lower() != b"cache-control"],
                    corpo=corpo,
                ),
            )
            enviados = _com_cache_control(cabecalhos, self._navegador)
            await send({**inicio, "headers": enviados})
            await send({"type": "http.response.body", "body": corpo})

        await self.app(scope, receive, capturar)
