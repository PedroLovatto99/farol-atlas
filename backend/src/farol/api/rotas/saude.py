"""GET /saude: estado do banco e da coleta. A rota só converte e devolve."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from farol.api.dependencias import sessao_da_requisicao
from farol.api.dtos import Saude
from farol.mapa import consultar_saude

roteador = APIRouter()


@roteador.get("/saude", response_model=Saude, responses={503: {"model": Saude}})
def obter_saude(
    resposta: Response, sessao: Annotated[Session, Depends(sessao_da_requisicao)]
) -> Saude:
    estado = consultar_saude(sessao)
    if not estado.banco_ok:
        resposta.status_code = 503
    return Saude(
        banco="ok" if estado.banco_ok else "falha",
        ultima_coleta_completa_em=estado.ultima_coleta_completa_em,
        ultima_tentativa_em=estado.ultima_tentativa_em,
        alertas_pendentes=estado.alertas_pendentes,
    )
