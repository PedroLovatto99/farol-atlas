"""Cliente HTTP educado para as coletas (constituição, princípio IV: coleta responsável).

- identifica-se com um User-Agent que traz um contato;
- consulta o robots.txt de cada host, uma vez, e só baixa o que ele permite;
- espera entre uma requisição e outra;
- segue os redirecionamentos um a um (até `MAXIMO_DE_DESVIOS`), consultando o robots.txt do host
  de cada destino e esperando entre os passos;
- ao cair na verificação humana ou ser bloqueado (HTTP 403/429), para e nunca insiste: toda
  requisição seguinte devolve o mesmo motivo sem tocar na rede.
"""

import re
import time
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, replace
from typing import Any, Protocol, cast
from urllib.parse import urljoin, urlsplit

import requests
from protego import Protego

NOME_DO_PROJETO = "FarolAtlas/0.1"
TEMPO_LIMITE_SEGUNDOS = 30.0
MAXIMO_DE_DESVIOS = 5
CODIGOS_DE_DESVIO = (301, 302, 303, 307, 308)

# Frases da página de verificação humana do gov.br
SINAIS_DE_VERIFICACAO = ("testing whether you are a human", "prevent automated spam", "captcha")

# Texto entre as tags de <script> e <style>: configuração e estilo, não conteúdo da página. Só ele
# é descartado; as tags (com os atributos `src`, `class`, `id`, `data-*`) e o texto visível ficam.
_CORPO_DE_SCRIPT_OU_ESTILO = re.compile(
    r"(<(script|style)\b[^>]*>).*?(</\2\s*>)", flags=re.IGNORECASE | re.DOTALL
)


class RespostaHttp(Protocol):
    status_code: int
    text: str
    encoding: str | None

    @property
    def headers(self) -> Mapping[str, str]: ...


class SessaoHttp(Protocol):
    """O que o cliente usa de `requests.Session` (e o que as sessões falsas dos testes têm)."""

    @property
    def headers(self) -> MutableMapping[Any, Any]: ...

    def get(self, url: str, *, timeout: float, allow_redirects: bool) -> RespostaHttp: ...


@dataclass(frozen=True)
class _Desvio:
    """Resposta de redirecionamento: para onde ir em seguida."""

    destino: str


@dataclass(frozen=True)
class Pagina:
    """Resultado de baixar uma URL: o conteúdo ou o motivo de não ter vindo."""

    url: str
    status: int | None
    html: str
    motivo: str | None  # None = conteúdo real
    url_final: str | None = None  # depois dos redirecionamentos; None = a própria `url`

    @property
    def ok(self) -> bool:
        return self.motivo is None

    @property
    def destino(self) -> str:
        """A URL de onde o conteúdo veio (a final, se houve redirecionamento)."""
        return self.url_final or self.url


class Baixador(Protocol):
    """O que as coletas usam do cliente HTTP (`ClienteEducado` ou um falso nos testes)."""

    interrompido_por: str | None

    def baixar(self, url: str) -> Pagina: ...


def parece_verificacao(html: str) -> bool:
    """A página é um desafio de verificação humana? (ignora o texto inline de script e estilo)"""
    texto = _CORPO_DE_SCRIPT_OU_ESTILO.sub(r"\1\3", html).lower()
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
        self.user_agent = (
            f"{NOME_DO_PROJETO} ({contato.strip()}; projeto pessoal) "
            f"python-requests/{requests.__version__}"
        )
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
        return self._seguir(url, com_robots=True)

    # ------------------------------------------------------------------ internos
    @staticmethod
    def _raiz_do_host(url: str) -> str:
        partes = urlsplit(url)
        return f"{partes.scheme}://{partes.netloc}"

    def _seguir(self, url: str, *, com_robots: bool) -> Pagina:
        """Pede `url` e segue os redirecionamentos; cada passo confere o robots.txt do seu host."""
        atual = url
        for _ in range(MAXIMO_DE_DESVIOS + 1):
            if self.interrompido_por is not None:
                return Pagina(url, None, "", self.interrompido_por)
            if com_robots:
                veto = self._vetar(atual)
                if veto is not None:
                    return Pagina(url, None, "", veto)
            resultado = self._requisitar(atual)
            if isinstance(resultado, _Desvio):
                atual = resultado.destino
                continue
            return replace(resultado, url=url, url_final=atual)
        return Pagina(url, None, "", "redirecionamentos demais")

    def _vetar(self, url: str) -> str | None:
        """Motivo de não poder baixar `url` (robots.txt), ou None se pode."""
        host = self._raiz_do_host(url)
        if host not in self._robots:
            self._robots[host] = self._ler_robots(host)
            if self.interrompido_por is not None:
                return self.interrompido_por
        regras = self._robots[host]
        if regras is None:
            return "robots.txt inacessível"
        if not regras.can_fetch(url, self.user_agent):
            return "proibida pelo robots.txt"
        return None

    def _requisitar(self, url: str) -> Pagina | _Desvio:
        try:
            resposta = self._sessao.get(url, timeout=TEMPO_LIMITE_SEGUNDOS, allow_redirects=False)
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
        if status in CODIGOS_DE_DESVIO:
            destino = resposta.headers.get("Location")
            if destino:
                return _Desvio(urljoin(url, destino))
        if status != 200:
            return Pagina(url, status, html, f"HTTP {status}")
        return Pagina(url, status, html, None)

    def _parar(self, url: str, status: int, motivo: str) -> Pagina:
        self.interrompido_por = motivo
        return Pagina(url, status, "", motivo)

    def _ler_robots(self, host: str) -> Protego | None:
        """Regras do host; `None` se o robots.txt não pôde ser lido (então nada é baixado)."""
        pagina = self._seguir(f"{host}/robots.txt", com_robots=False)
        if self.interrompido_por is not None:
            return None
        if pagina.status == 404:
            return Protego.parse("")  # sem robots.txt, sem restrições
        if not pagina.ok:
            return None
        return Protego.parse(pagina.html)
