"""GET /vistos: a situação de visto de cada território, para o modo "Vistos" do globo.

A rota só converte e devolve. O frontend a busca sob demanda, ao escolher o modo "Vistos".
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from farol.api.dependencias import relogio_da_requisicao, sessao_da_requisicao
from farol.api.dtos import (
    Fonte,
    ObservacaoDeVisto,
    OrigemDoVisto,
    Permanencia,
    SituacaoDeVisto,
    SituacaoNoGlobo,
    TerritorioDeVisto,
    TipoDePermanencia,
    Visto,
    VistosDoMapa,
)
from farol.infra import Relogio
from farol.vistos import FonteDosVistos, VisaoDosVistos, VisaoDoVisto, montar_vistos_do_mapa

roteador = APIRouter()


def fonte_para_dto(fonte: FonteDosVistos) -> Fonte:
    return Fonte(nome=fonte.nome, url=fonte.url, licenca=fonte.licenca)


def visto_para_dto(visao: VisaoDoVisto) -> Visto:
    return Visto(
        situacao=SituacaoDeVisto(visao.situacao.value),
        motivo_outra_situacao=visao.motivo_outra_situacao,
        rotulo_original=visao.rotulo_original,
        aceita_rg=visao.aceita_rg,
        varia_conforme_motivo=visao.varia_conforme_motivo,
        permanencia=(
            Permanencia(
                tipo=TipoDePermanencia(visao.permanencia.tipo.value), texto=visao.permanencia.texto
            )
            if visao.permanencia
            else None
        ),
        observacoes=[
            ObservacaoDeVisto(texto_original=o.texto_original, traducao=o.traducao)
            for o in visao.observacoes
        ],
        origem=OrigemDoVisto(visao.origem.value) if visao.origem else None,
        soberano_nome=visao.soberano_nome,
        territorio_nome=visao.territorio_nome,
        dado_de=visao.dado_de,
        desatualizado=visao.desatualizado,
        fonte=fonte_para_dto(visao.fonte),
    )


def _para_dto(visao: VisaoDosVistos) -> VistosDoMapa:
    return VistosDoMapa(
        dados_obtidos=visao.dados_obtidos,
        coletado_em=visao.coletado_em,
        desatualizado=visao.desatualizado,
        fonte=fonte_para_dto(visao.fonte),
        territorios=[
            TerritorioDeVisto(
                codigo=t.codigo, situacao=SituacaoNoGlobo(t.situacao.value), aceita_rg=t.aceita_rg
            )
            for t in visao.territorios
        ],
    )


@roteador.get("/vistos", response_model=VistosDoMapa, operation_id="obterVistos")
def obter_vistos(
    sessao: Annotated[Session, Depends(sessao_da_requisicao)],
    relogio: Annotated[Relogio, Depends(relogio_da_requisicao)],
) -> VistosDoMapa:
    return _para_dto(montar_vistos_do_mapa(sessao, relogio))
