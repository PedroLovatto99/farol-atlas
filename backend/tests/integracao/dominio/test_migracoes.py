"""Migrações do Alembic: sobem e descem sem erro e o esquema bate com os modelos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

from farol.dominio.modelos import Base

TABELAS = {
    "territorio",
    "posto",
    "execucao_coleta",
    "alerta",
    "classificacao",
    "nivel_territorio",
    "fonte_dados",
}


def test_subir_e_descer_sem_erro(engine_teste: Engine, configuracao_alembic: Config) -> None:
    configuracao = configuracao_alembic
    command.downgrade(configuracao, "base")
    assert TABELAS.isdisjoint(inspect(engine_teste).get_table_names())
    command.upgrade(configuracao, "head")
    assert set(inspect(engine_teste).get_table_names()) >= TABELAS


def test_esquema_migrado_bate_com_os_modelos(engine_teste: Engine) -> None:
    with engine_teste.connect() as conexao:
        contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
        diferencas = compare_metadata(contexto, Base.metadata)
    assert diferencas == []
