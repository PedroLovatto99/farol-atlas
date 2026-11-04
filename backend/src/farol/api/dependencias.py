"""Dependências do FastAPI compartilhadas pelas rotas."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from farol.api.composicao import FonteDoPainelDaApi
from farol.chat import ServicoDoChat
from farol.infra import Relogio, RelogioDoSistema, abrir_sessao


def sessao_da_requisicao() -> Iterator[Session]:
    """Uma sessão do banco por requisição; confirma ao fim (nenhuma rota grava nada)."""
    with abrir_sessao() as sessao:
        yield sessao


def relogio_da_requisicao() -> Relogio:
    """O relógio do sistema; os testes o trocam para controlar a hora."""
    return RelogioDoSistema()


def servico_do_chat(
    request: Request,
    sessao: Annotated[Session, Depends(sessao_da_requisicao)],
    relogio: Annotated[Relogio, Depends(relogio_da_requisicao)],
) -> ServicoDoChat:
    """O serviço do chat com os dados do painel e o modelo do app (None se `LLM_CHAT` for vazia)."""
    return ServicoDoChat(FonteDoPainelDaApi(sessao, relogio), request.app.state.modelo_do_chat)
