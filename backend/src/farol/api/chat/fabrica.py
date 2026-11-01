"""Monta o pipeline do chat de uma requisição, com as peças de verdade.

É uma dependência do FastAPI que devolve uma FÁBRICA, e não o pipeline: a rota só a chama depois
de saber que o chat está ligado, então um chat desligado nem lê a configuração do modelo. Sem a
chave do chat ou sem modelo configurado, o pipeline nasce sem modelo e responde com o erro de
serviço indisponível; a busca nos alertas cai na busca por texto se faltar o embeddador.
"""

from collections.abc import Callable, Sequence
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from farol.api.chat.ferramentas import ConsultaDeNivelDoSite, ResolvedorDePaisesDoSite
from farol.api.dependencias import configuracoes_da_requisicao, sessao_da_requisicao
from farol.chat import (
    ModeloDoChat,
    PipelineDoChat,
    RecuperadorDeTrechos,
    criar_embeddador,
    criar_modelo_do_chat,
)
from farol.dominio import TrechoAlertaRepositorio
from farol.infra import Configuracoes, obter_logger

_log = obter_logger("farol.api")


class _SemEmbeddings:
    """Embeddador ausente: a recuperação cai na busca por texto."""

    def vetorizar_documentos(self, textos: Sequence[str]) -> list[Sequence[float]]:
        raise RuntimeError("embeddings indisponíveis")

    def vetorizar_pergunta(self, texto: str) -> Sequence[float]:
        raise RuntimeError("embeddings indisponíveis")


def _modelo(configuracoes: Configuracoes) -> ModeloDoChat | None:
    try:
        return criar_modelo_do_chat(configuracoes)
    except Exception as erro:
        _log.warning("modelo do chat indisponível: %s", type(erro).__name__)
        return None


def montar_pipeline(sessao: Session, configuracoes: Configuracoes) -> PipelineDoChat:
    try:
        embeddador = criar_embeddador(configuracoes)
        modelo_de_embeddings, dimensoes = embeddador.modelo, embeddador.dimensoes
    except Exception as erro:
        _log.warning("embeddings do chat indisponíveis: %s", type(erro).__name__)
        embeddador = None
        modelo_de_embeddings = configuracoes.embeddings_modelo
        dimensoes = configuracoes.embeddings_dimensoes
    return PipelineDoChat(
        modelo=_modelo(configuracoes),
        resolvedor=ResolvedorDePaisesDoSite(sessao),
        consulta_de_nivel=ConsultaDeNivelDoSite(sessao),
        recuperador=RecuperadorDeTrechos(
            sessao,
            embeddador or _SemEmbeddings(),
            modelo=modelo_de_embeddings,
            dimensoes=dimensoes,
            limite=configuracoes.chat_trechos_por_pergunta,
        ),
        alertas=TrechoAlertaRepositorio(sessao),
        limite_de_trechos=configuracoes.chat_trechos_por_pergunta,
    )


def fabrica_do_pipeline(
    sessao: Annotated[Session, Depends(sessao_da_requisicao)],
    configuracoes: Annotated[Configuracoes, Depends(configuracoes_da_requisicao)],
) -> Callable[[], PipelineDoChat]:
    return lambda: montar_pipeline(sessao, configuracoes)
