"""Extrai a tabela de repartições consulares: cada país → o posto (ou postos) que o atende.

Coluna 1: o país, com link para a página dele. Coluna 2: um ou mais links, um por posto, que
levam ao site do posto (hoje em `*.itamaraty.gov.br`, com redirecionamento para `www.gov.br`).
"""

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

# "Consulado-Geral do Brasil em Chengdu" → "Chengdu"
_PREFIXO_DO_POSTO = re.compile(
    r"^(embaixada|consulado[- ]geral|consulado|vice-consulado|escrit[óo]rio[^,]*?)"
    r"\s+do\s+brasil\s+(em|junto\s+[àa])\s+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LinkDePosto:
    nome: str  # a cidade do posto, como a tabela escreve
    url: str


@dataclass(frozen=True)
class LinhaDeReparticao:
    pais: str
    pais_url: str | None
    postos: tuple[LinkDePosto, ...]


def _limpar(texto: str) -> str:
    """Espaços colapsados e sem as marcas de nota de rodapé (`**`)."""
    return " ".join(texto.replace("*", " ").split())


def _nome_pela_url(url: str) -> str:
    """Nome de reserva para um link sem texto (há um na tabela): o subdomínio do posto
    (`cartum.itamaraty.gov.br` → `cartum`) ou o último trecho do caminho."""
    partes = urlsplit(url)
    rotulo = partes.netloc.split(".")[0]
    if rotulo != "www" and partes.netloc.endswith("itamaraty.gov.br"):
        return rotulo
    return ""


def _nome_do_posto(link: Tag, url: str) -> str:
    """O `title` costuma ter o nome inteiro (o texto às vezes vem partido em dois pedaços)."""
    titulo = link.get("title")
    bruto = titulo if isinstance(titulo, str) and titulo.strip() else link.get_text(" ", strip=True)
    nome = _PREFIXO_DO_POSTO.sub("", _limpar(bruto))
    return nome or _nome_pela_url(url)


def _nome_do_pais(celula: Tag, url: str | None) -> str:
    """O texto da célula; sem texto (acontece na tabela real), o último trecho do link do país."""
    nome = _limpar(celula.get_text(" ", strip=True))
    if nome or url is None:
        return nome
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()


def _postos_da_celula(celula: Tag, url_da_pagina: str) -> tuple[LinkDePosto, ...]:
    postos: dict[str, LinkDePosto] = {}
    for link in celula.select("a[href]"):
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        url = urljoin(url_da_pagina, href.strip())
        nome = _nome_do_posto(link, url)
        if nome and url not in postos:  # há links repetidos e vazios soltos no HTML da tabela
            postos[url] = LinkDePosto(nome=nome, url=url)
    return tuple(postos.values())


def extrair_reparticoes(html: str, url_da_pagina: str) -> tuple[LinhaDeReparticao, ...]:
    """Linhas de dados da tabela; a primeira (cabeçalho, sem link de país) fica de fora."""
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.select_one("#content-core table") or soup.select_one("table")
    if tabela is None:
        return ()
    linhas: list[LinhaDeReparticao] = []
    for posicao, tr in enumerate(tabela.select("tr")):
        celulas = tr.find_all("td")
        if len(celulas) < 2:
            continue
        link_do_pais = celulas[0].select_one("a[href]")
        if posicao == 0 and link_do_pais is None:
            continue
        href = link_do_pais.get("href") if link_do_pais is not None else None
        pais_url = urljoin(url_da_pagina, href) if isinstance(href, str) and href else None
        pais = _nome_do_pais(celulas[0], pais_url)
        if not pais:
            continue
        linhas.append(
            LinhaDeReparticao(
                pais=pais,
                pais_url=pais_url,
                postos=_postos_da_celula(celulas[1], url_da_pagina),
            )
        )
    return tuple(linhas)
