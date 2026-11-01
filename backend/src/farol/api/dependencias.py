"""Dependências do FastAPI compartilhadas pelas rotas."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from farol.infra import Configuracoes, Relogio, RelogioDoSistema, abrir_sessao


def sessao_da_requisicao() -> Iterator[Session]:
    """Uma sessão do banco por requisição; confirma ao fim (as rotas são só de leitura)."""
    with abrir_sessao() as sessao:
        yield sessao


def configuracoes_da_requisicao(requisicao: Request) -> Configuracoes:
    """As configurações com que o app foi montado (as dos testes, nos testes)."""
    configuracoes: Configuracoes = requisicao.app.state.configuracoes
    return configuracoes


def relogio_da_requisicao() -> Relogio:
    """O relógio do sistema; os testes o trocam para controlar a hora."""
    return RelogioDoSistema()
