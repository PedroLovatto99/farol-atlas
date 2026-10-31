"""Migrações do Alembic: sobem e descem sem erro e o esquema bate com os modelos."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from farol.dominio.modelos import Base

TABELAS = {
    "territorio",
    "posto",
    "execucao_coleta",
    "alerta",
    "classificacao",
    "nivel_territorio",
    "fonte_dados",
    "coleta_vistos",
    "requisito_visto",
    "mudanca_retida",
    "item_para_revisao",
    "versao_dados",
}
TABELAS_DA_001 = TABELAS - {
    "coleta_vistos",
    "requisito_visto",
    "mudanca_retida",
    "item_para_revisao",
    "versao_dados",
}
TABELAS_DA_002 = TABELAS - TABELAS_DA_001


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


def test_downgrade_para_0002_remove_so_as_tabelas_de_vistos(
    engine_teste: Engine, configuracao_alembic: Config
) -> None:
    """A 0003 só acrescenta: descer para a 0002 apaga as quatro e deixa a 001 intacta."""
    command.upgrade(configuracao_alembic, "head")
    with engine_teste.begin() as conexao:
        conexao.execute(
            text("insert into territorio (codigo, nome_pt, tipo) values ('ZZ', 'Teste', 'pais')")
        )
    colunas_antes = {
        tabela: [c["name"] for c in inspect(engine_teste).get_columns(tabela)]
        for tabela in TABELAS_DA_001
    }
    try:
        command.downgrade(configuracao_alembic, "0002")

        tabelas = set(inspect(engine_teste).get_table_names())
        assert TABELAS_DA_002.isdisjoint(tabelas)
        assert tabelas >= TABELAS_DA_001
        colunas_depois = {
            tabela: [c["name"] for c in inspect(engine_teste).get_columns(tabela)]
            for tabela in TABELAS_DA_001
        }
        assert colunas_depois == colunas_antes
        with engine_teste.connect() as conexao:
            assert conexao.execute(text("select count(*) from territorio")).scalar_one() == 1

        command.upgrade(configuracao_alembic, "head")

        assert set(inspect(engine_teste).get_table_names()) >= TABELAS_DA_002
        with engine_teste.connect() as conexao:
            assert conexao.execute(text("select count(*) from territorio")).scalar_one() == 1
    finally:
        command.upgrade(configuracao_alembic, "head")
        with engine_teste.begin() as conexao:
            conexao.execute(text("delete from territorio where codigo = 'ZZ'"))
