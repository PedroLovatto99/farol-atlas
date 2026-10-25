"""GET /paises/{codigo}: o painel de um país ou dependência. A rota só converte e devolve."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from farol.api.dependencias import sessao_da_requisicao
from farol.api.dtos import (
    AlertaDoPais,
    Erro,
    Fonte,
    FontePostos,
    Nivel,
    NivelRegional,
    Pais,
    PostoNoPainel,
    Regiao,
    TipoTerritorio,
)
from farol.mapa import PostoNoPainel as PostoVisao
from farol.mapa import TerritorioNaoEncontrado, VisaoDoPainel, montar_painel

roteador = APIRouter()


def _posto(p: PostoVisao) -> PostoNoPainel:
    return PostoNoPainel(
        id=p.id,
        tipo=p.tipo,
        cidade=p.cidade,
        pais=p.pais,
        grupo=p.grupo,
        endereco=p.endereco,
        telefone_plantao=p.telefone_plantao,
        contato_coletado_em=p.contato_coletado_em,
        contato_fonte_url=p.contato_fonte_url,
    )


def _para_dto(visao: VisaoDoPainel) -> Pais:
    return Pais(
        codigo=visao.codigo,
        nome=visao.nome,
        tipo=TipoTerritorio(visao.tipo.value),
        soberano=visao.soberano,
        bandeira=visao.bandeira,
        identidade_do_soberano=visao.identidade_do_soberano,
        nivel=Nivel(visao.nivel.value),
        regioes=[Regiao(nome=r.nome, nivel=NivelRegional(r.nivel.value)) for r in visao.regioes],
        regiao_unica_do_alerta=visao.regiao_unica_do_alerta,
        observacao=visao.observacao,
        observacao_no_topo=visao.observacao_no_topo,
        eh_brasil=visao.eh_brasil,
        alertas=[
            AlertaDoPais(
                titulo=a.titulo,
                url=a.url,
                publicado_em=a.publicado_em,
                modificado_em=a.modificado_em,
                define_nivel=a.define_nivel,
                situacao_normalizada=a.situacao_normalizada,
                pendente=a.pendente,
            )
            for a in visao.alertas
        ],
        postos=[_posto(p) for p in visao.postos],
        posto_responsavel=_posto(visao.posto_responsavel) if visao.posto_responsavel else None,
        sem_posto_indicado=visao.sem_posto_indicado,
        fonte_postos=(
            FontePostos(
                conferido_em=visao.fonte_postos.conferido_em,
                fontes=[
                    Fonte(nome=f.nome, url=f.url, licenca=f.licenca)
                    for f in visao.fonte_postos.fontes
                ],
            )
            if visao.fonte_postos
            else None
        ),
    )


@roteador.get(
    "/paises/{codigo}",
    response_model=Pais,
    responses={404: {"model": Erro}, 422: {"model": Erro}},
    operation_id="obterPais",
)
def obter_pais(
    codigo: Annotated[
        str,
        Path(
            pattern=r"^[A-Z]{2,3}$",
            description=(
                "Código do território (ISO-2 ou código de dependência, de 2 a 3 letras como IOA),"
                " como em /mapa."
            ),
        ),
    ],
    sessao: Annotated[Session, Depends(sessao_da_requisicao)],
) -> Pais:
    try:
        return _para_dto(montar_painel(sessao, codigo))
    except TerritorioNaoEncontrado:
        raise HTTPException(status_code=404, detail="Território não encontrado") from None
