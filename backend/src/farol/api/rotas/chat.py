"""POST /chat: valida, gasta a ficha do IP, chama o serviço e converte. A regra fica no `chat`."""

import math
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from farol.api.dependencias import servico_do_chat
from farol.api.dtos import (
    Erro,
    PerguntaDoChat,
    RespostaDoChat,
    TipoDeRespostaDoChat,
    TrechoDoChat,
)
from farol.chat import ServicoDoChat, limite_de_perguntas

roteador = APIRouter()

RESPOSTA_DO_LIMITE: dict[str, Any] = {
    "model": Erro,
    "headers": {"Retry-After": {"schema": {"type": "integer"}}},
}


@roteador.post(
    "/chat",
    response_model=RespostaDoChat,
    responses={422: {"model": Erro}, 429: RESPOSTA_DO_LIMITE},
    operation_id="perguntarAoChat",
)
def perguntar_ao_chat(
    corpo: PerguntaDoChat,
    request: Request,
    servico: Annotated[ServicoDoChat, Depends(servico_do_chat)],
) -> RespostaDoChat:
    # O IP é o que o `IpReal` já trocou; a ficha só é gasta depois de validar o corpo (D6)
    ip = request.client.host if request.client else "desconhecido"
    espera = request.app.state.balde_do_chat.tentar(ip)
    if espera is not None:
        detalhe = limite_de_perguntas(
            request.app.state.chat_perguntas_por_hora, math.ceil(espera / 60)
        )
        raise HTTPException(429, detail=detalhe, headers={"Retry-After": str(espera)})

    resposta = servico.responder(corpo.pergunta)
    return RespostaDoChat(
        tipo=TipoDeRespostaDoChat(resposta.tipo.value),
        codigo=resposta.codigo,
        paragrafos=[
            [TrechoDoChat(texto=t.texto, url=t.url) for t in paragrafo]
            for paragrafo in resposta.paragrafos
        ],
    )
