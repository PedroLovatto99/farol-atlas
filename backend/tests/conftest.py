"""Fixtures compartilhadas dos testes do backend.

Testes de unidade não precisam de banco. Os de integração usam o PostgreSQL de teste, que sobe com
`docker compose --profile teste up -d postgres-teste` (porta só em 127.0.0.1:5433). A URL vem de
`DATABASE_URL_TESTE`, lida do ambiente ou do `.env` da raiz.
"""

import html
import json
import os
import re
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from farol.dominio import CategoriaDeVisto, ColetaVistos, RequisitoVisto, ResultadoDaColetaDeVistos
from farol.infra import Pagina
from farol.vistos import ResumoDaColetaDeVistos, ServicoDeColetaDeVistos, Tradutor
from farol.vistos.fonte import TABELA_DE_TERRITORIOS, TABELA_NAO_RECONHECIDOS, LinhaDaFonte

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
RAIZ_REPOSITORIO = RAIZ_BACKEND.parent
URL_TESTE_PADRAO = "postgresql+psycopg://farol:farol@127.0.0.1:5433/farol_teste"


# --------------------------------------------------------------------------- relógio falso
@dataclass
class RelogioFalso:
    """Relógio controlado pelo teste; cumpre o protocolo `farol.infra.Relogio`."""

    instante: datetime = field(default_factory=lambda: datetime(2026, 10, 23, 12, 0, tzinfo=UTC))

    def agora(self) -> datetime:
        return self.instante

    def avancar(self, **tempo: float) -> None:
        self.instante += timedelta(**tempo)


@pytest.fixture
def relogio() -> RelogioFalso:
    return RelogioFalso()


# --------------------------------------------------------------------------- gov.br falso
URL_DA_LISTA_FALSA = "https://www.gov.br/mre/alertas"
FUSO_DE_BRASILIA = timezone(timedelta(hours=-3))


class GovBrFalso:
    """Portal Consular de mentira: monta lista e páginas de alertas e faz o papel do cliente HTTP.

    Cumpre o protocolo `Baixador` do serviço de coleta (`baixar` e `interrompido_por`). Nenhum
    teste acessa a internet.
    """

    def __init__(self) -> None:
        self.paginas: dict[str, Pagina] = {}
        self.pedidos: list[str] = []
        self.interrompido_por: str | None = None
        self.itens: list[tuple[str, str, datetime]] = []  # (titulo, url, publicado_em)
        self.originais: dict[str, Pagina] = {}

    # ----------------------------------------------------------- montagem
    @staticmethod
    def url_do_alerta(n: int) -> str:
        return f"https://www.gov.br/mre/alertas/a{n}"

    @staticmethod
    def html_da_lista(itens: list[tuple[str, str, datetime]], proxima: str | None = None) -> str:
        blocos = "".join(
            '<div class="conteudo">'
            f'<h2 class="titulo"><a href="{url}">{titulo}</a></h2>'
            f'<span class="descricao"><span class="data">'
            f"{publicado.astimezone(FUSO_DE_BRASILIA):%d/%m/%Y}</span></span></div>"
            for titulo, url, publicado in itens
        )
        link = f'<nav><a href="{proxima}" class="next">Próximo</a></nav>' if proxima else ""
        return f'<div class="listagem-noticias-com-foto">{blocos}</div>{link}'

    @staticmethod
    def html_do_alerta(
        titulo: str,
        texto: str,
        publicado: datetime,
        modificado: datetime | None = None,
        categoria: str = "Brasileiro indo para o exterior",
    ) -> str:
        modificado = modificado or publicado
        return (
            "<html><head>"
            '<script type="application/ld+json">'
            '{"@type": "NewsArticle", '
            f'"datePublished": "{publicado.isoformat()}", '
            f'"dateModified": "{modificado.isoformat()}"}}'
            "</script></head><body>"
            f'<h1 class="documentFirstHeading">{titulo}</h1>'
            f'<span id="form-widgets-categoria">{categoria}</span>'
            '<div id="content-core"><div property="rnews:articleBody">'
            f"<p>{texto}</p></div></div></body></html>"
        )

    def publicar_alertas(self, quantidade: int, *, a_partir_de: int = 0) -> list[str]:
        """Cria `quantidade` alertas (lista e páginas) e devolve as URLs."""
        urls = []
        for n in range(a_partir_de, a_partir_de + quantidade):
            url = self.url_do_alerta(n)
            publicado = datetime(2026, 6, 1, 15, 0, tzinfo=FUSO_DE_BRASILIA) + timedelta(days=n)
            titulo = f"Alerta {n}"
            self.itens.append((titulo, url, publicado))
            self.publicar_pagina(url, titulo, f"Texto do alerta {n}.", publicado)
            self.originais[url] = self.paginas[url]
            urls.append(url)
        self.publicar_lista()
        return urls

    def restaurar(self, *urls: str) -> None:
        """Volta a página dos alertas ao que `publicar_alertas` criou (desfaz falhas e edições)."""
        for url in urls:
            self.paginas[url] = self.originais[url]

    def publicar_pagina(
        self,
        url: str,
        titulo: str,
        texto: str,
        publicado: datetime,
        modificado: datetime | None = None,
    ) -> None:
        html = self.html_do_alerta(titulo, texto, publicado, modificado)
        self.paginas[url] = Pagina(url, 200, html, None)

    def publicar_lista(self, url: str = URL_DA_LISTA_FALSA, proxima: str | None = None) -> None:
        html = self.html_da_lista(self.itens, proxima)
        self.paginas[url] = Pagina(url, 200, html, None)

    def falhar(self, url: str, motivo: str = "HTTP 500") -> None:
        self.paginas[url] = Pagina(url, None, "", motivo)

    def remover_da_lista(self, url: str) -> None:
        self.itens = [i for i in self.itens if i[1] != url]
        self.publicar_lista()

    # ----------------------------------------------------------- cliente
    def baixar(self, url: str) -> Pagina:
        if self.interrompido_por is not None:
            return Pagina(url, None, "", self.interrompido_por)
        self.pedidos.append(url)
        pagina = self.paginas.get(url, Pagina(url, 404, "", "HTTP 404"))
        if pagina.motivo and (
            pagina.motivo.startswith("bloqueado") or "verificação humana" in pagina.motivo
        ):
            self.interrompido_por = pagina.motivo
        return pagina


@pytest.fixture
def govbr() -> GovBrFalso:
    return GovBrFalso()


# --------------------------------------------------------------------------- Wikipédia falsa
HTML_DA_WIKIPEDIA = (
    RAIZ_BACKEND
    / "tests"
    / "fixtures"
    / "wikipedia"
    / "visa_requirements_for_brazilian_citizens.html"
)
URL_DO_ARTIGO_FALSO = "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens"


@pytest.fixture(scope="session")
def html_da_wikipedia() -> str:
    """A página real do artigo (revisão 1380975986), salva em `tests/fixtures/wikipedia/`."""
    return HTML_DA_WIKIPEDIA.read_text(encoding="utf-8")


def _html_das_notas(notas: str) -> str:
    """Notas com várias linhas viram itens separados por `<br>`, como a fonte os entrega."""
    return "<br>".join(html.escape(linha) for linha in notas.split("\n"))


def html_de_vistos(
    linhas: Sequence[LinhaDaFonte], editada_em: datetime, revisao: int = 1000
) -> str:
    """Monta uma página mínima com as três tabelas do artigo, a partir das linhas já normalizadas.

    Serve para os testes alterarem uma linha (rótulo, nota, nome) sem mexer no HTML de 1,5 MB.
    `extrair_linhas` devolve de volta as mesmas linhas.
    """
    cabecalho_principal = (
        "<tr><th>Country</th><th>Visa requirement</th><th>Allowed stay</th>"
        "<th>Notes (excluding departure fees)</th><th>Reciprocity</th></tr>"
    )
    cabecalho_territorios = "<tr><th>Territory</th><th>Conditions of access</th><th>Notes</th></tr>"

    def tabela(titulo: str, cabecalho: str, corpo: str) -> str:
        return f'<h2>{titulo}</h2><table class="wikitable">{cabecalho}{corpo}</table>'

    principal = "".join(
        f"<tr><td>{html.escape(linha.nome)}</td><td>{html.escape(linha.rotulo)}</td>"
        f"<td>{html.escape(linha.permanencia)}</td><td>{_html_das_notas(linha.notas)}</td>"
        "<td></td></tr>"
        for linha in linhas
        if linha.tabela not in (TABELA_NAO_RECONHECIDOS, TABELA_DE_TERRITORIOS)
    )

    def corpo_de_territorios(tabela_lida: str) -> str:
        corpo, grupo_atual = "", None
        for linha in linhas:
            if linha.tabela != tabela_lida:
                continue
            if linha.grupo is not None and linha.grupo != grupo_atual:
                corpo += f'<tr><th colspan="3">{html.escape(linha.grupo)}</th></tr>'
                grupo_atual = linha.grupo
            corpo += (
                f"<tr><td>{html.escape(linha.nome)}</td><td>{html.escape(linha.rotulo)}</td>"
                f"<td>{_html_das_notas(linha.notas)}</td></tr>"
            )
        return corpo

    json_ld = json.dumps(
        {"@type": "Article", "dateModified": editada_em.strftime("%Y-%m-%dT%H:%M:%SZ")}
    )
    return (
        "<html><head>"
        f'<script type="application/ld+json">{json_ld}</script>'
        f'<script>RLCONF={{"wgRevisionId":{revisao}}};</script></head><body>'
        + tabela("Visa requirements", cabecalho_principal, principal)
        + tabela(
            "Unrecognized or partially recognized countries",
            cabecalho_territorios,
            corpo_de_territorios(TABELA_NAO_RECONHECIDOS),
        )
        + tabela(
            "Dependent and autonomous territories",
            cabecalho_territorios,
            corpo_de_territorios(TABELA_DE_TERRITORIOS),
        )
        + "</body></html>"
    )


class WikipediaFalsa:
    """Wikipédia de mentira: serve o artigo e simula os problemas que a coleta de vistos trata.

    Cumpre o protocolo `Baixador` (`baixar` e `interrompido_por`), como o `ClienteEducado`:
    bloqueio (403/429) e verificação humana interrompem tudo; o `robots.txt` que proíbe o
    artigo responde sem baixar a página (o pedido não é registrado). Nenhum teste acessa a internet.
    """

    def __init__(self, html: str | None = None, url: str = URL_DO_ARTIGO_FALSO) -> None:
        self.url = url
        self.paginas: dict[str, Pagina] = {}
        self.pedidos: list[str] = []
        self.interrompido_por: str | None = None
        self._proibidas: set[str] = set()
        if html is not None:
            self.publicar(html)

    # ----------------------------------------------------------- montagem
    def publicar(self, html: str, url: str | None = None) -> None:
        alvo = url or self.url
        self.paginas[alvo] = Pagina(alvo, 200, html, None)

    def publicar_linhas(
        self,
        linhas: Sequence[LinhaDaFonte],
        editada_em: datetime,
        revisao: int = 1000,
        url: str | None = None,
    ) -> None:
        """Serve uma página montada a partir das linhas (veja `html_de_vistos`)."""
        self.publicar(html_de_vistos(linhas, editada_em, revisao), url)

    def falhar_com_status(self, status: int, url: str | None = None) -> None:
        """Erro do servidor (5xx) ou outro status que não seja de bloqueio."""
        alvo = url or self.url
        self.paginas[alvo] = Pagina(alvo, status, "", f"HTTP {status}")

    def falhar_com_erro_de_conexao(self, url: str | None = None) -> None:
        alvo = url or self.url
        self.paginas[alvo] = Pagina(alvo, None, "", "erro de conexão: Timeout")

    def bloquear(self, status: int = 403, url: str | None = None) -> None:
        """403 ou 429: a coleta para e não insiste."""
        alvo = url or self.url
        self.paginas[alvo] = Pagina(alvo, status, "", f"bloqueado (HTTP {status})")

    def pedir_verificacao_humana(self, url: str | None = None) -> None:
        alvo = url or self.url
        self.paginas[alvo] = Pagina(alvo, 200, "", "caiu na verificação humana")

    def proibir_pelo_robots(self, url: str | None = None) -> None:
        """O `robots.txt` passa a proibir a URL: a página nem é baixada."""
        self._proibidas.add(url or self.url)

    # ----------------------------------------------------------- cliente
    def baixar(self, url: str) -> Pagina:
        if self.interrompido_por is not None:
            return Pagina(url, None, "", self.interrompido_por)
        if url in self._proibidas:
            return Pagina(url, None, "", "proibida pelo robots.txt")
        self.pedidos.append(url)
        pagina = self.paginas.get(url, Pagina(url, 404, "", "HTTP 404"))
        if pagina.motivo and (
            pagina.motivo.startswith("bloqueado") or "verificação humana" in pagina.motivo
        ):
            self.interrompido_por = pagina.motivo
        return pagina


@pytest.fixture
def wikipedia(html_da_wikipedia: str) -> WikipediaFalsa:
    """Wikipédia falsa já servindo a página real do artigo."""
    return WikipediaFalsa(html_da_wikipedia)


class ColetorDeVistos(Protocol):
    def __call__(self, html: str, tradutor: Tradutor | None = None) -> ResumoDaColetaDeVistos: ...


class GravadorDeVisto(Protocol):
    def __call__(
        self,
        codigo: str,
        *,
        categoria: CategoriaDeVisto = ...,
        rotulo: str = ...,
        observacoes: Sequence[tuple[str, str | None]] = ...,
        aceita_rg: bool = ...,
    ) -> RequisitoVisto: ...


@pytest.fixture
def coletar_vistos(sessao: Session, relogio: RelogioFalso) -> ColetorDeVistos:
    """Roda uma coleta de vistos de verdade sobre a página dada, no banco já semeado do teste.

    O relógio deve estar a mais de 24 h da última edição do artigo (19/10/2026), ou a coleta é
    adiada. O padrão dos testes (23/10/2026) serve.
    """

    def coletar(html: str, tradutor: Tradutor | None = None) -> ResumoDaColetaDeVistos:
        resumo = ServicoDeColetaDeVistos(sessao, WikipediaFalsa(html), relogio, tradutor).coletar()
        assert resumo.valida, resumo.motivo
        return resumo

    return coletar


@pytest.fixture
def gravar_visto(sessao: Session, relogio: RelogioFalso) -> GravadorDeVisto:
    """Grava à mão o visto exibido de um território (com a sua coleta válida), sem passar pela
    coleta. Serve aos testes da API que só precisam de um dado qualquer, ou de texto malicioso.
    `observacoes` são pares (texto, tradução)."""

    def gravar(
        codigo: str,
        *,
        categoria: CategoriaDeVisto = CategoriaDeVisto.ISENTO,
        rotulo: str = "Visa not required",
        observacoes: Sequence[tuple[str, str | None]] = (),
        aceita_rg: bool = False,
    ) -> RequisitoVisto:
        instante = relogio.agora()
        coleta = ColetaVistos(
            iniciada_em=instante,
            finalizada_em=instante,
            resultado=ResultadoDaColetaDeVistos.VALIDA,
            linhas_lidas=1,
            paises_reconhecidos=1,
        )
        sessao.add(coleta)
        sessao.flush()
        requisito = RequisitoVisto(
            territorio_codigo=codigo,
            categoria=categoria,
            rotulo_original=rotulo,
            linhas_fonte=[],
            hash_fonte="0" * 64,
            aceita_rg=aceita_rg,
            observacoes=[
                {"texto": texto, "hash": f"{n:064d}", "traducao": traducao}
                for n, (texto, traducao) in enumerate(observacoes)
            ],
            lido_em=instante,
            coleta_id=coleta.id,
        )
        sessao.add(requisito)
        sessao.flush()
        return requisito

    return gravar


# --------------------------------------------------------------------------- tradutor falso
class TradutorFalso:
    """Tradutor de mentira: cumpre o protocolo `farol.vistos.Tradutor` sem modelo nem rede.

    Registra cada lote recebido em `lotes` e devolve `"[pt] " + texto` (as quebras de linha do
    texto seguem como estão). `falhar = True` faz toda chamada levantar erro, e `falhar_no_lote`
    faz falhar só a chamada de número N (a partir de 0).
    """

    nome_do_modelo = "falso:tradutor"

    def __init__(self) -> None:
        self.lotes: list[list[str]] = []
        self.falhar = False
        self.falhar_no_lote: int | None = None

    @property
    def textos(self) -> list[str]:
        """Todos os textos recebidos, na ordem."""
        return [texto for lote in self.lotes for texto in lote]

    def traduzir(self, textos: Sequence[str]) -> list[str]:
        numero = len(self.lotes)
        self.lotes.append(list(textos))
        if self.falhar or self.falhar_no_lote == numero:
            raise RuntimeError("tradutor falso: falha pedida pelo teste")
        return [f"[pt] {texto}" for texto in textos]


@pytest.fixture
def tradutor_falso() -> TradutorFalso:
    return TradutorFalso()


# --------------------------------------------------------------------------- banco de teste
def _config_alembic(url: str) -> Config:
    configuracao = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    configuracao.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return configuracao


def _resolver_url_teste() -> str:
    """Variável de ambiente, depois o `.env` da raiz do repositório, depois o padrão do compose."""
    do_ambiente = os.environ.get("DATABASE_URL_TESTE")
    if do_ambiente:
        return do_ambiente
    do_arquivo = dotenv_values(RAIZ_REPOSITORIO / ".env").get("DATABASE_URL_TESTE")
    return do_arquivo or URL_TESTE_PADRAO


@pytest.fixture(scope="session")
def url_banco_teste() -> str:
    return _resolver_url_teste()


@pytest.fixture(scope="session")
def configuracao_alembic(url_banco_teste: str) -> Config:
    return _config_alembic(url_banco_teste)


@pytest.fixture(scope="session")
def engine_teste(url_banco_teste: str) -> Iterator[Engine]:
    """Engine do banco de teste, com as migrações aplicadas do zero."""
    engine = create_engine(url_banco_teste, pool_pre_ping=True)
    limite = time.monotonic() + 20
    while True:
        try:
            with engine.connect() as conexao:
                conexao.execute(text("select 1"))
            break
        except OperationalError as erro:
            if time.monotonic() > limite:
                engine.dispose()
                pytest.fail(
                    "PostgreSQL de teste indisponível. Suba com: "
                    "docker compose --profile teste up -d postgres-teste\n"
                    f"({re.sub(r':[^:@/]+@', ':***@', url_banco_teste)}): {erro.orig}"
                )
            time.sleep(0.5)
    # Banco sempre limpo: apaga o esquema (o teste de migrações cobre o downgrade)
    with engine.begin() as conexao:
        conexao.execute(text("drop schema public cascade"))
        conexao.execute(text("create schema public"))
    command.upgrade(_config_alembic(url_banco_teste), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def sessao(engine_teste: Engine) -> Iterator[Session]:
    """Sessão que desfaz tudo ao fim do teste (a sessão usa um SAVEPOINT dentro da transação)."""
    conexao = engine_teste.connect()
    transacao = conexao.begin()
    sessao = Session(bind=conexao, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield sessao
    finally:
        sessao.close()
        transacao.rollback()
        conexao.close()


# --------------------------------------------------------------------------- contador de consultas
class ContadorDeConsultas:
    """Conta as consultas SQL reais (SELECT, INSERT, UPDATE, DELETE) enviadas ao banco."""

    _COMANDOS = ("select", "insert", "update", "delete")

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.consultas: list[str] = []

    @property
    def total(self) -> int:
        return len(self.consultas)

    def _contar(
        self,
        conexao: Connection,
        cursor: DBAPICursor,
        statement: str,
        parametros: object,
        contexto: ExecutionContext | None,
        executemany: bool,
    ) -> None:
        if statement.lstrip().lower().startswith(self._COMANDOS):
            self.consultas.append(statement)

    def __enter__(self) -> "ContadorDeConsultas":
        self.consultas = []  # cada bloco `with` conta do zero
        event.listen(self._engine, "before_cursor_execute", self._contar)
        return self

    def __exit__(self, *_: object) -> None:
        event.remove(self._engine, "before_cursor_execute", self._contar)


@pytest.fixture
def contar_consultas(engine_teste: Engine) -> ContadorDeConsultas:
    """Uso: `with contar_consultas as c: ...; assert c.total <= 6`."""
    return ContadorDeConsultas(engine_teste)
