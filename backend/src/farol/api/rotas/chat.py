"""POST /chat: a pergunta ao chat, com a resposta em fluxo de eventos (`text/event-stream`).

Sem regra de negócio: recusa com 503 se o chat está desligado, valida o corpo (Pydantic), chama o
pipeline sob o prazo e converte cada evento em DTO. Erros antes do fluxo voltam como JSON comum;
os do meio do caminho (serviço fora, tempo esgotado) chegam como evento `erro`.
"""

from collections.abc import AsyncIterator, Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.sse import format_sse_event
from starlette.responses import Response

from farol.api.chat.fabrica import fabrica_do_pipeline
from farol.api.dependencias import configuracoes_da_requisicao
from farol.api.dtos import (
    CitacaoDoChat,
    ErroDoChat,
    EventoErro,
    EventoProgresso,
    EventoResposta,
    PerguntaDoChat,
    SituacaoDaResposta,
)
from farol.chat import (
    EventoDeProgresso,
    EventoDeResposta,
    EventoDoChat,
    MensagemAnterior,
    PipelineDoChat,
    RespostaMontada,
    com_prazo,
)
from farol.infra import Configuracoes

roteador = APIRouter()

CHAT_DESLIGADO = "O chat está desligado no momento. O mapa e o painel dos países seguem no ar."


class ChatDesligado(Exception):
    """`CHAT_HABILITADO=false`: o app responde 503 antes de abrir o banco ou montar o pipeline."""


def exigir_chat_ligado(
    configuracoes: Annotated[Configuracoes, Depends(configuracoes_da_requisicao)],
) -> None:
    if not configuracoes.chat_habilitado:
        raise ChatDesligado


def resposta_do_chat_desligado() -> JSONResponse:
    erro = ErroDoChat(detalhe=CHAT_DESLIGADO, codigo="chat_desligado")
    return JSONResponse(erro.model_dump(mode="json"), status_code=503)


class RespostaEmEventos(StreamingResponse):
    media_type = "text/event-stream"


def _referencia(nome: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{nome}"}


def _em_json(esquema: str, descricao: str) -> dict[str, Any]:
    return {
        "description": descricao,
        "content": {"application/json": {"schema": _referencia(esquema)}},
    }


# O 200 é um fluxo: o OpenAPI descreve cada item; os esquemas dos eventos são acrescentados em
# `components` pelo app (veja `app.py`), que também publica o `x-eventos`
RESPOSTA_EM_FLUXO: dict[str, Any] = {
    "description": "Fluxo de eventos (progresso, depois resposta ou erro)",
    "content": {
        "text/event-stream": {
            "itemSchema": {
                "type": "object",
                "properties": {
                    "event": {"type": "string", "enum": ["progresso", "resposta", "erro"]},
                    "data": {
                        "type": "string",
                        "contentMediaType": "application/json",
                        "contentSchema": {
                            "oneOf": [
                                _referencia("EventoProgresso"),
                                _referencia("EventoResposta"),
                                _referencia("EventoErro"),
                            ]
                        },
                    },
                },
            }
        }
    },
}


def resposta_para_dto(resposta: RespostaMontada) -> EventoResposta:
    return EventoResposta(
        situacao=SituacaoDaResposta(resposta.situacao),
        texto=resposta.texto,
        cartoes=[],  # os cartões de nível, visto e postos chegam com a US2
        citacoes=[
            CitacaoDoChat(
                tipo=c.tipo,
                titulo=c.titulo,
                data=c.data,
                url=c.url,
                vigor=c.vigor,
                trecho=c.trecho,
                licenca=c.licenca,
            )
            for c in resposta.citacoes
        ],
        avisos=list(resposta.avisos),
    )


def _em_sse(evento: EventoDoChat) -> bytes:
    dto: EventoProgresso | EventoResposta | EventoErro
    if isinstance(evento, EventoDeProgresso):
        nome, dto = "progresso", EventoProgresso(etapa=evento.etapa, mensagem=evento.mensagem)
    elif isinstance(evento, EventoDeResposta):
        nome, dto = "resposta", resposta_para_dto(evento.resposta)
    else:
        nome = "erro"
        dto = EventoErro(
            codigo=evento.codigo,
            mensagem=evento.mensagem,
            pode_tentar_de_novo=evento.pode_tentar_de_novo,
        )
    return format_sse_event(data_str=dto.model_dump_json(), event=nome)


async def _fluxo(eventos: AsyncIterator[EventoDoChat]) -> AsyncIterator[bytes]:
    async for evento in eventos:
        yield _em_sse(evento)


@roteador.post(
    "/chat",
    operation_id="perguntarAoChat",
    summary="Pergunta ao chat, com resposta em fluxo de eventos",
    response_class=RespostaEmEventos,
    # resolvida antes das outras dependências: chat desligado não toca no banco
    dependencies=[Depends(exigir_chat_ligado)],
    responses={
        200: RESPOSTA_EM_FLUXO,
        # os erros antes do fluxo são JSON comum; o esquema vai por referência porque o tipo
        # padrão desta rota é o do fluxo (o `ErroDoChat` é publicado pelo app, como os eventos)
        422: _em_json("Erro", "Pergunta ou histórico inválidos"),
        429: _em_json("ErroDoChat", "Limite por hora ou teto do dia"),
        503: _em_json("ErroDoChat", "Chat desligado por configuração"),
    },
    openapi_extra={
        "x-eventos": {
            "progresso": _referencia("EventoProgresso"),
            "resposta": _referencia("EventoResposta"),
            "erro": _referencia("EventoErro"),
        }
    },
)
async def perguntar_ao_chat(
    corpo: PerguntaDoChat,
    configuracoes: Annotated[Configuracoes, Depends(configuracoes_da_requisicao)],
    fabrica: Annotated[Callable[[], PipelineDoChat], Depends(fabrica_do_pipeline)],
) -> Response:
    pipeline = fabrica()
    historico = [MensagemAnterior(m.papel, m.texto) for m in corpo.historico]
    eventos = com_prazo(
        pipeline.perguntar(corpo.pergunta, historico), configuracoes.chat_tempo_maximo_segundos
    )
    return RespostaEmEventos(
        _fluxo(eventos),
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
