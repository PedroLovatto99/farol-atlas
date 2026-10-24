"""GET /mapa: tudo o que o mapa precisa, numa chamada só. A rota só converte e devolve."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from farol.api.dependencias import relogio_da_requisicao, sessao_da_requisicao
from farol.api.dtos import (
    Mapa,
    Nivel,
    NivelRegional,
    PaisSemPosto,
    PostoNoMapa,
    Regiao,
    TerritorioNoMapa,
    TipoTerritorio,
)
from farol.infra import Relogio
from farol.mapa import VisaoDoMapa, montar_mapa

roteador = APIRouter()


def _para_dto(visao: VisaoDoMapa) -> Mapa:
    return Mapa(
        dados_obtidos=visao.dados_obtidos,
        atualizado_em=visao.atualizado_em,
        desatualizado=visao.desatualizado,
        territorios=[
            TerritorioNoMapa(
                codigo=t.codigo,
                nome=t.nome,
                rotulo_busca=t.rotulo_busca,
                termos_busca=list(t.termos_busca),
                tipo=TipoTerritorio(t.tipo.value),
                soberano=t.soberano,
                bandeira=t.bandeira,
                identidade_do_soberano=t.identidade_do_soberano,
                nivel=Nivel(t.nivel.value),
                regioes=[
                    Regiao(nome=r.nome, nivel=NivelRegional(r.nivel.value)) for r in t.regioes
                ],
                observacao=t.observacao,
            )
            for t in visao.territorios
        ],
        postos=[
            PostoNoMapa(
                id=p.id,
                territorio=p.territorio,
                tipo=p.tipo,
                cidade=p.cidade,
                latitude=p.latitude,
                longitude=p.longitude,
                grupo=p.grupo,
            )
            for p in visao.postos
        ],
        paises_sem_posto=[
            PaisSemPosto(
                territorio=p.territorio,
                latitude=p.latitude,
                longitude=p.longitude,
                posto_responsavel_id=p.posto_responsavel_id,
            )
            for p in visao.paises_sem_posto
        ],
    )


@roteador.get("/mapa", response_model=Mapa, operation_id="obterMapa")
def obter_mapa(
    sessao: Annotated[Session, Depends(sessao_da_requisicao)],
    relogio: Annotated[Relogio, Depends(relogio_da_requisicao)],
) -> Mapa:
    return _para_dto(montar_mapa(sessao, relogio))
