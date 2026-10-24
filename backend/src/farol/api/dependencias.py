"""Dependências do FastAPI compartilhadas pelas rotas."""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from farol.infra import abrir_sessao


def sessao_da_requisicao() -> Iterator[Session]:
    """Uma sessão do banco por requisição; confirma ao fim (as rotas são só de leitura)."""
    with abrir_sessao() as sessao:
        yield sessao
