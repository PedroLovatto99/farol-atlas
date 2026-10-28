"""A fonte dos vistos: a página do artigo da Wikipédia, lida como texto puro.

Só a página do artigo é usada (nunca `/w/api.php` nem `/api/`, que o `robots.txt` proíbe). Daqui
saem a data da última edição e as linhas das três tabelas; nada de HTML da fonte é guardado.
"""

import copy
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from farol.vistos.normalizacao import normalizar, normalizar_rotulo

URL_DO_ARTIGO = "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens"
NOME_DA_FONTE = "Wikipédia: Visa requirements for Brazilian citizens"
LICENCA_DA_FONTE = "CC BY-SA"

TABELA_PRINCIPAL = "principal"
TABELA_NAO_RECONHECIDOS = "nao_reconhecidos"
TABELA_DE_TERRITORIOS = "territorios"

_CABECALHO_DE_TERRITORIOS = ("territory", "conditions of access", "notes")
_NOMES_DOS_MESES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
_MESES = {nome: numero for numero, nome in enumerate(_NOMES_DOS_MESES, start=1)}
_RODAPE = re.compile(
    r"last edited on (\d{1,2}) ([A-Za-z]+) (\d{4}), at (\d{1,2}):(\d{2})", flags=re.IGNORECASE
)
_REVISAO = re.compile(r'"wgRevisionId"\s*:\s*(\d+)')


class ErroDeFormato(Exception):
    """A página não tem o formato esperado: a coleta é rejeitada e o site segue como está."""


@dataclass(frozen=True)
class EdicaoDaFonte:
    ultima_edicao: datetime  # em UTC
    revisao: int | None  # `wgRevisionId`


@dataclass(frozen=True)
class LinhaDaFonte:
    """Uma linha de dados de uma das três tabelas, com todo o texto já normalizado."""

    tabela: str
    grupo: str | None  # o soberano, na tabela de territórios
    nome: str
    rotulo: str
    permanencia: str  # só a tabela principal tem a coluna; nas outras fica vazio (O3)
    notas: str  # vazio quando a célula está em branco; itens de lista, um por linha

    def como_dicionario(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ArtigoLido:
    ultima_edicao: datetime
    revisao: int | None
    linhas: tuple[LinhaDaFonte, ...]


# --------------------------------------------------------------------------- data da edição
def _data_do_json_ld(sopa: BeautifulSoup) -> datetime | None:
    for bloco in sopa.select('script[type="application/ld+json"]'):
        try:
            conteudo: Any = json.loads(bloco.string or bloco.get_text())
        except ValueError:
            continue
        for item in conteudo if isinstance(conteudo, list) else [conteudo]:
            valor = item.get("dateModified") if isinstance(item, dict) else None
            if not isinstance(valor, str):
                continue
            try:
                data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            except ValueError:
                continue
            return data.replace(tzinfo=UTC) if data.tzinfo is None else data.astimezone(UTC)
    return None


def _data_do_rodape(sopa: BeautifulSoup) -> datetime | None:
    rodape = sopa.select_one("#footer-info-lastmod")
    achado = _RODAPE.search(rodape.get_text(" ") if rodape else sopa.get_text(" "))
    if achado is None:
        return None
    dia, mes, ano, hora, minuto = achado.groups()
    numero_do_mes = _MESES.get(mes.lower())
    if numero_do_mes is None:
        return None
    try:
        return datetime(int(ano), numero_do_mes, int(dia), int(hora), int(minuto), tzinfo=UTC)
    except ValueError:
        return None


def _edicao(sopa: BeautifulSoup, html: str) -> EdicaoDaFonte:
    data = _data_do_json_ld(sopa) or _data_do_rodape(sopa)
    if data is None:
        raise ErroDeFormato("a página não informa a data da última edição")
    revisao = _REVISAO.search(html)
    return EdicaoDaFonte(data, int(revisao.group(1)) if revisao else None)


def extrair_edicao(html: str) -> EdicaoDaFonte:
    """Data da última edição (`dateModified` do JSON-LD; na falta, o rodapé) e a revisão."""
    return _edicao(BeautifulSoup(html, "html.parser"), html)


# --------------------------------------------------------------------------- tabelas
def _texto_da_celula(celula: Tag, *, rotulo: bool = False) -> str:
    """Texto puro da célula: sem notas de rodapé, sem script e com os itens de lista em linhas.

    A barra só é uniformizada nos rótulos (`rotulo=True`); o resto fica como na fonte.
    """
    copia = copy.copy(celula)
    for tag in copia.find_all(["sup", "script", "style"]):
        tag.decompose()
    for tag in copia.find_all(["br", "li", "p", "div"]):
        tag.insert_before("\n")
        tag.insert_after("\n")
    texto = copia.get_text("")
    return normalizar_rotulo(texto) if rotulo else normalizar(texto)


def _cabecalho(tabela: Tag) -> tuple[str, ...]:
    for linha in tabela.find_all("tr"):
        celulas = linha.find_all("th")
        if celulas:
            return tuple(_texto_da_celula(c).casefold() for c in celulas)
    return ()


def _e_a_tabela_principal(cabecalho: tuple[str, ...]) -> bool:
    return (
        len(cabecalho) >= 4
        and cabecalho[:3] == ("country", "visa requirement", "allowed stay")
        and cabecalho[3].startswith("notes")
    )


def _nome_da_secao(tabela: Tag) -> str:
    titulo = tabela.find_previous(["h2", "h3"])
    return _texto_da_celula(titulo).casefold() if isinstance(titulo, Tag) else ""


def _linhas_da_tabela_principal(tabela: Tag) -> list[LinhaDaFonte]:
    linhas = []
    for linha in tabela.find_all("tr"):
        celulas = linha.find_all("td")
        if not celulas:
            continue  # cabeçalho
        if len(celulas) < 4:
            raise ErroDeFormato("linha da tabela principal com menos de 4 colunas")
        nome, permanencia, notas = (_texto_da_celula(celulas[i]) for i in (0, 2, 3))
        rotulo = _texto_da_celula(celulas[1], rotulo=True)
        linhas.append(LinhaDaFonte(TABELA_PRINCIPAL, None, nome, rotulo, permanencia, notas))
    return linhas


def _linhas_de_territorios(tabela: Tag, nome_da_tabela: str) -> list[LinhaDaFonte]:
    """Linha de uma célula só = grupo (o soberano); as de três células são dados."""
    linhas: list[LinhaDaFonte] = []
    grupo: str | None = None
    for linha in tabela.find_all("tr"):
        celulas = linha.find_all(["th", "td"])
        if len(celulas) == 1:  # linha de grupo (a fonte usa `th` ou `td` com colspan)
            grupo = _texto_da_celula(celulas[0]) or None
            continue
        if not linha.find("td"):
            continue  # cabeçalho
        if len(celulas) != 3:
            raise ErroDeFormato("linha de território com número inesperado de colunas")
        nome, notas = _texto_da_celula(celulas[0]), _texto_da_celula(celulas[2])
        rotulo = _texto_da_celula(celulas[1], rotulo=True)
        linhas.append(LinhaDaFonte(nome_da_tabela, grupo, nome, rotulo, "", notas))
    return linhas


def _linhas(sopa: BeautifulSoup) -> list[LinhaDaFonte]:
    principal: list[LinhaDaFonte] | None = None
    nao_reconhecidos: list[LinhaDaFonte] | None = None
    territorios: list[LinhaDaFonte] | None = None
    for tabela in sopa.select("table.wikitable"):
        cabecalho = _cabecalho(tabela)
        if _e_a_tabela_principal(cabecalho):
            if principal is not None:
                raise ErroDeFormato("mais de uma tabela principal de países")
            principal = _linhas_da_tabela_principal(tabela)
        elif cabecalho[:3] == _CABECALHO_DE_TERRITORIOS:
            secao = _nome_da_secao(tabela)
            if "unrecognized" in secao and nao_reconhecidos is None:
                nao_reconhecidos = _linhas_de_territorios(tabela, TABELA_NAO_RECONHECIDOS)
            elif "dependent and autonomous" in secao and territorios is None:
                territorios = _linhas_de_territorios(tabela, TABELA_DE_TERRITORIOS)
    if principal is None or nao_reconhecidos is None or territorios is None:
        raise ErroDeFormato("faltam tabelas esperadas ou os cabeçalhos mudaram")
    return principal + nao_reconhecidos + territorios


def extrair_linhas(html: str) -> list[LinhaDaFonte]:
    """As linhas de dados das três tabelas (a lista "Other territories" não é lida)."""
    return _linhas(BeautifulSoup(html, "html.parser"))


def ler_artigo(html: str) -> ArtigoLido:
    """Lê a página uma vez: data da edição, revisão e linhas. `ErroDeFormato` se algo faltar."""
    sopa = BeautifulSoup(html, "html.parser")
    edicao = _edicao(sopa, html)
    return ArtigoLido(edicao.ultima_edicao, edicao.revisao, tuple(_linhas(sopa)))
