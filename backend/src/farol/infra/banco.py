"""Único ponto de configuração do banco: engine e sessões do SQLAlchemy.

Só os repositórios (em `farol.dominio`) falam SQL; este módulo apenas entrega as sessões.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from farol.infra.config import obter_configuracoes
from farol.infra.versao import subir_se_escreveu


def criar_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def criar_fabrica_de_sessoes(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@lru_cache
def obter_engine() -> Engine:
    return criar_engine(obter_configuracoes().database_url.get_secret_value())


@lru_cache
def obter_fabrica_de_sessoes() -> sessionmaker[Session]:
    return criar_fabrica_de_sessoes(obter_engine())


@contextmanager
def abrir_sessao(
    fabrica: sessionmaker[Session] | None = None, *, versiona: bool = True
) -> Iterator[Session]:
    """Abre uma sessão; confirma ao sair sem erro e desfaz se houver exceção.

    Se a sessão gravou algo, sobe a versão dos dados na mesma transação (veja `versao.py`). Com
    `versiona=False` não sobe: é para o que não muda o que o site mostra (as contagens do chat),
    para não esvaziar o cache de leitura a cada escrita.
    """
    sessao = (fabrica or obter_fabrica_de_sessoes())()
    try:
        yield sessao
        sessao.flush()
        if versiona:
            subir_se_escreveu(sessao)
        else:
            sessao.info.pop("escreveu", None)
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()
