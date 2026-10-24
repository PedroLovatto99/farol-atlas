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
from datetime import UTC, datetime, timedelta
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
        event.listen(self._engine, "before_cursor_execute", self._contar)
        return self

    def __exit__(self, *_: object) -> None:
        event.remove(self._engine, "before_cursor_execute", self._contar)


@pytest.fixture
def contar_consultas(engine_teste: Engine) -> ContadorDeConsultas:
    """Uso: `with contar_consultas as c: ...; assert c.total <= 6`."""
    return ContadorDeConsultas(engine_teste)
