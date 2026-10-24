"""Extrai a página de listagem de alertas do Portal Consular (bloco `.conteudo` por alerta)."""

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

FUSO_DO_PORTAL = ZoneInfo("America/Sao_Paulo")
_DATA_DA_LISTA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_ROTULO_DE_PROXIMA = re.compile(r"^\s*(próxim[oa]|seguinte|avançar|›|»)", re.IGNORECASE)
_ROTULO_DE_ANTERIOR = re.compile(r"^\s*(anterior|voltar|‹|«)", re.IGNORECASE)


@dataclass(frozen=True)
class ItemDaLista:
    titulo: str
    url: str
    publicado_em: datetime  # a lista só traz a data: meia-noite em São Paulo, em UTC


@dataclass(frozen=True)
class ListaDeAlertas:
    itens: tuple[ItemDaLista, ...]
    proxima_pagina: str | None


def data_da_lista(texto: str) -> datetime | None:
    """`dd/mm/aaaa` (data de Brasília) como instante UTC à meia-noite local."""
    achado = _DATA_DA_LISTA.search(texto)
    if achado is None:
        return None
    dia, mes, ano = (int(parte) for parte in achado.groups())
    try:
        local = datetime(ano, mes, dia, tzinfo=FUSO_DO_PORTAL)
    except ValueError:
        return None
    return local.astimezone(ZoneInfo("UTC"))


def _item(bloco: Tag, url_da_pagina: str) -> ItemDaLista | None:
    link = bloco.select_one("h2.titulo a")
    data = bloco.select_one("span.data")
    href = link.get("href") if link else None
    if link is None or not isinstance(href, str) or data is None:
        return None
    publicado_em = data_da_lista(data.get_text(" ", strip=True))
    if publicado_em is None:
        return None
    return ItemDaLista(
        titulo=" ".join(link.get_text(" ", strip=True).split()),
        url=urljoin(url_da_pagina, href),
        publicado_em=publicado_em,
    )


def _valores(tag: Tag, atributo: str) -> list[str]:
    """Atributo multivalorado (`rel`, `class`) como lista de textos."""
    valor = tag.get(atributo)
    if valor is None:
        return []
    return valor.split() if isinstance(valor, str) else list(valor)


def _proxima_pagina(soup: BeautifulSoup, url_da_pagina: str) -> str | None:
    """Link "próxima página" (Plone: `b_start`), ou `rel="next"`. Nunca o "anterior"."""
    for link in soup.select("a[href], link[href]"):
        href = link.get("href")
        if not isinstance(href, str) or href.startswith("#") or not href.strip():
            continue
        rel = _valores(link, "rel")
        classes = _valores(link, "class")
        texto = link.get_text(" ", strip=True)
        if _ROTULO_DE_ANTERIOR.match(texto) or "previous" in classes or "prev" in rel:
            continue
        marcado_como_proximo = "next" in rel or "next" in classes
        rotulado = bool(_ROTULO_DE_PROXIMA.match(texto)) and "b_start" in href
        if marcado_como_proximo or rotulado:
            return urljoin(url_da_pagina, href)
    return None


def extrair_lista_de_alertas(html: str, url_da_pagina: str) -> ListaDeAlertas:
    soup = BeautifulSoup(html, "html.parser")
    blocos = soup.select(".listagem-noticias-com-foto .conteudo") or soup.select(
        "#content-core .conteudo"
    )
    itens = tuple(item for bloco in blocos if (item := _item(bloco, url_da_pagina)) is not None)
    return ListaDeAlertas(itens=itens, proxima_pagina=_proxima_pagina(soup, url_da_pagina))
