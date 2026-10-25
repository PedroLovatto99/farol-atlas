"""Extrai a página de um alerta: título, categoria, datas (JSON-LD primeiro) e texto."""

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from farol.infra import FUSO_DE_BRASILIA

_PUBLICADO_EM = re.compile(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{1,2})h(\d{2}))?")


class ErroDeExtracao(Exception):
    """A página não tem o formato esperado; o alerta fica como página não lida."""


@dataclass(frozen=True)
class AlertaExtraido:
    titulo: str
    categoria: str | None
    publicado_em: datetime
    modificado_em: datetime | None
    texto: str  # espaços colapsados
    html_corpo: str  # guardado para reprocessar; nunca vai para o frontend


def _instante(valor: object) -> datetime | None:
    if not isinstance(valor, str):
        return None
    try:
        instante = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=FUSO_DE_BRASILIA)
    return instante.astimezone(UTC)


def _datas_do_json_ld(soup: BeautifulSoup) -> tuple[datetime | None, datetime | None]:
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            dados: Any = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and dados.get("@type") in ("NewsArticle", "Article"):
            return _instante(dados.get("datePublished")), _instante(dados.get("dateModified"))
    return None, None


def _publicado_em_da_pagina(soup: BeautifulSoup) -> datetime | None:
    """Reserva: o texto "Publicado em 10/07/2026 16h35" (horário de Brasília)."""
    valor = soup.select_one("#plone-document-byline .documentPublished .value")
    achado = _PUBLICADO_EM.search(valor.get_text(" ", strip=True)) if valor else None
    if achado is None:
        return None
    dia, mes, ano, hora, minuto = achado.groups()
    try:
        local = datetime(
            int(ano), int(mes), int(dia), int(hora or 0), int(minuto or 0), tzinfo=FUSO_DE_BRASILIA
        )
    except ValueError:
        return None
    return local.astimezone(UTC)


def extrair_alerta(html: str) -> AlertaExtraido:
    soup = BeautifulSoup(html, "html.parser")
    titulo = soup.select_one("h1.documentFirstHeading")
    corpo = soup.select_one('#content-core [property="rnews:articleBody"]') or soup.select_one(
        "#content-core"
    )
    if titulo is None or corpo is None:
        raise ErroDeExtracao("página fora do formato esperado (sem título ou corpo)")

    publicado, modificado = _datas_do_json_ld(soup)
    publicado = publicado or _publicado_em_da_pagina(soup)
    if publicado is None:
        raise ErroDeExtracao("página sem data de publicação")

    categoria = soup.select_one("#form-widgets-categoria")
    return AlertaExtraido(
        titulo=" ".join(titulo.get_text(" ", strip=True).split()),
        categoria=categoria.get_text(" ", strip=True) if categoria else None,
        publicado_em=publicado,
        modificado_em=modificado,
        texto=" ".join(corpo.get_text(" ", strip=True).split()),
        html_corpo=str(corpo),
    )
