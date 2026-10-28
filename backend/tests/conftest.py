"""Fixtures compartilhadas dos testes do backend.

Testes de unidade não precisam de banco. Os de integração usam o PostgreSQL de teste, que sobe com
`docker compose --profile teste up -d postgres-teste` (porta só em 127.0.0.1:5433). A URL vem de
`DATABASE_URL_TESTE`, lida do ambiente ou do `.env` da raiz.
"""

import os
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.engine.interfaces import DBAPICursor, ExecutionContext
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from farol.infra import Pagina

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
