"""Cache da API com o banco de verdade: uma coleta nova invalida o que estava guardado."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from farol.api.app import criar_app, sessao_da_requisicao
from farol.dominio import ExecucaoColeta, TipoExecucao
from farol.infra import Configuracoes, abrir_sessao, criar_fabrica_de_sessoes

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas


class Tempo:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


@pytest.fixture
def fabrica(engine_teste: Engine) -> Iterator[sessionmaker[Session]]:
    yield criar_fabrica_de_sessoes(engine_teste)
    with engine_teste.begin() as conexao:
        conexao.execute(text("TRUNCATE execucao_coleta RESTART IDENTITY CASCADE"))


def _cliente(fabrica: sessionmaker[Session], tempo: Tempo) -> TestClient:
    config = Configuracoes(database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"))
    app = criar_app(config, relogio_monotonico=tempo)

    def fornecer() -> Iterator[Session]:
        with abrir_sessao(fabrica) as sessao:
            yield sessao

    app.dependency_overrides[sessao_da_requisicao] = fornecer
    return TestClient(app)


def test_uma_escrita_confirmada_faz_o_cache_ser_refeito_em_ate_15_segundos(
    fabrica: sessionmaker[Session], contar_consultas: "ContadorDeConsultas"
) -> None:
    tempo = Tempo()
    http = _cliente(fabrica, tempo)
    assert http.get("/api/v1/vistos").status_code == 200  # enche o cache

    with contar_consultas as contador:
        http.get("/api/v1/vistos")
    assert contador.total == 0  # nem a versão foi consultada de novo: tudo da memória

    with abrir_sessao(fabrica) as sessao:  # o worker grava uma coleta
        sessao.add(ExecucaoColeta(tipo=TipoExecucao.ALERTAS, iniciada_em=datetime.now(UTC)))

    tempo.agora += 15
    with contar_consultas as contador:
        resposta = http.get("/api/v1/vistos")
    assert resposta.status_code == 200
    assert contador.total > 1  # a versão mudou: a resposta foi refeita no banco

    with contar_consultas as contador:
        http.get("/api/v1/vistos")
    assert contador.total == 0  # e voltou a ficar guardada


def test_sem_escrita_o_cache_so_expira_pelo_ttl(
    fabrica: sessionmaker[Session], contar_consultas: "ContadorDeConsultas"
) -> None:
    tempo = Tempo()
    http = _cliente(fabrica, tempo)
    http.get("/api/v1/vistos")
    tempo.agora += 299
    with contar_consultas as contador:
        http.get("/api/v1/vistos")
    assert contador.total == 1  # só a consulta da versão (o intervalo de 15 s já passou)
    tempo.agora += 1
    with contar_consultas as contador:
        http.get("/api/v1/vistos")
    assert contador.total > 1  # passou dos 5 minutos: refeito
