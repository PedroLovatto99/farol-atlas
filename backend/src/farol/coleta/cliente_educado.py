"""Cliente HTTP educado para o gov.br (constituição, princípio IV: coleta responsável).

- identifica-se com um User-Agent que traz um contato;
- consulta o robots.txt de cada host, uma vez, e só baixa o que ele permite;
- espera entre uma requisição e outra;
- ao cair na verificação humana ou ser bloqueado (HTTP 403/429), para e nunca insiste: toda
  requisição seguinte devolve o mesmo motivo sem tocar na rede.
"""

import time
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

import requests
from protego import Protego

NOME_DO_PROJETO = "FarolAtlas/0.1"
TEMPO_LIMITE_SEGUNDOS = 30.0

# Frases da página de verificação humana do gov.br
SINAIS_DE_VERIFICACAO = ("testing whether you are a human", "prevent automated spam", "captcha")


class RespostaHttp(Protocol):
    status_code: int
    text: str
    encoding: str | None


class SessaoHttp(Protocol):
    """O que o cliente usa de `requests.Session` (e o que as sessões falsas dos testes têm)."""

    @property
    def headers(self) -> MutableMapping[Any, Any]: ...

    def get(self, url: str, *, timeout: float) -> RespostaHttp: ...


@dataclass(frozen=True)
class Pagina:
    """Resultado de baixar uma URL: o conteúdo ou o motivo de não ter vindo."""

    url: str
    status: int | None
    html: str
    motivo: str | None  # None = conteúdo real

    @property
    def ok(self) -> bool:
        return self.motivo is None


def parece_verificacao(html: str) -> bool:
    texto = html.lower()
    return any(sinal in texto for sinal in SINAIS_DE_VERIFICACAO)


class ClienteEducado:
    def __init__(
        self,
        contato: str,
        *,
        pausa_segundos: float = 2.0,
        sessao: SessaoHttp | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        if not contato.strip():
            raise ValueError("informe um contato (CONTATO_COLETA) para o User-Agent da coleta")
        self.user_agent = f"{NOME_DO_PROJETO} (projeto pessoal; contato: {contato.strip()})"
        self._pausa = pausa_segundos
        self._dormir = dormir
        # `requests.Session` cumpre o protocolo; só os tipos de `get` e `headers` são mais largos
        self._sessao: SessaoHttp = (
            sessao if sessao is not None else cast(SessaoHttp, requests.Session())
        )
        self._sessao.headers.update({"User-Agent": self.user_agent})
        self._sessao.headers.update({"Accept-Language": "pt-BR,pt;q=0.9"})
        self._robots: dict[str, Protego | None] = {}
        self.interrompido_por: str | None = None

    def baixar(self, url: str) -> Pagina:
        """Baixa uma página. Nunca levanta erro de rede: o motivo vem em `Pagina.motivo`."""
        if self.interrompido_por is not None:
            return Pagina(url, None, "", self.interrompido_por)

        host = self._raiz_do_host(url)
        if host not in self._robots:
            self._robots[host] = self._ler_robots(host)
            if self.interrompido_por is not None:
                return Pagina(url, None, "", self.interrompido_por)
        regras = self._robots[host]
        if regras is None:
            return Pagina(url, None, "", "robots.txt inacessível")
        if not regras.can_fetch(url, self.user_agent):
            return Pagina(url, None, "", "proibida pelo robots.txt")

        return self._requisitar(url)

    # ------------------------------------------------------------------ internos
    @staticmethod
    def _raiz_do_host(url: str) -> str:
        partes = urlsplit(url)
        return f"{partes.scheme}://{partes.netloc}"

    def _requisitar(self, url: str) -> Pagina:
        try:
            resposta = self._sessao.get(url, timeout=TEMPO_LIMITE_SEGUNDOS)
        except requests.RequestException as erro:
            return Pagina(url, None, "", f"erro de conexão: {type(erro).__name__}")
        finally:
            self._dormir(self._pausa)

        html = resposta.text
        status = resposta.status_code
        if parece_verificacao(html):
            return self._parar(url, status, "caiu na verificação humana")
        if status in (403, 429):
            return self._parar(url, status, f"bloqueado (HTTP {status})")
        if status != 200:
            return Pagina(url, status, html, f"HTTP {status}")
        return Pagina(url, status, html, None)

    def _parar(self, url: str, status: int, motivo: str) -> Pagina:
        self.interrompido_por = motivo
        return Pagina(url, status, "", motivo)

    def _ler_robots(self, host: str) -> Protego | None:
        """Regras do host; `None` se o robots.txt não pôde ser lido (então nada é baixado)."""
        pagina = self._requisitar(f"{host}/robots.txt")
        if self.interrompido_por is not None:
            return None
        if pagina.status == 404:
            return Protego.parse("")  # sem robots.txt, sem restrições
        if not pagina.ok:
            return None
        return Protego.parse(pagina.html)
