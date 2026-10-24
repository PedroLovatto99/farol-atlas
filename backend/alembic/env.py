"""Ambiente do Alembic.

A URL do banco vem, nesta ordem, de: `sqlalchemy.url` já definido na configuração (os testes
fazem isso), ou da variável de ambiente DATABASE_URL.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from farol.dominio.modelos import Base

configuracao = context.config
metadata_alvo = Base.metadata


def _url() -> str:
    url = configuracao.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Defina DATABASE_URL (ou sqlalchemy.url) para rodar as migrações.")
    return url


def rodar_offline() -> None:
    context.configure(url=_url(), target_metadata=metadata_alvo, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def rodar_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as conexao:
        context.configure(connection=conexao, target_metadata=metadata_alvo, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    rodar_offline()
else:
    rodar_online()
