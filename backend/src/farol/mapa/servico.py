"""Monta a visão de `GET /mapa`: níveis resolvidos, postos e países sem posto, numa chamada.

Número fixo de consultas, qualquer que seja a quantidade de países, postos ou alertas (princípio
III): última coleta completa (1), territórios (1), postos (1) e alertas confirmados com suas
classificações e níveis (3). A regra do nível roda em Python sobre essas linhas (`nivel.py`).
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from farol.dominio import (
    AlertaRepositorio,
    ExecucaoRepositorio,
    PostoRepositorio,
    Territorio,
    TerritorioRepositorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.infra import Relogio, obter_logger
from farol.mapa.nivel import AlertaParaNivel, TerritorioParaNivel, calcular_niveis, titulo_cita
from farol.mapa.preparo import alerta_para_nivel, grupo_do_posto, nomes_para_titulo
from farol.mapa.visoes import PaisSemPosto, PostoNoMapa, TerritorioNoMapa, VisaoDoMapa

LIMITE_DE_DADOS_ANTIGOS = timedelta(days=3)  # FR-041

_log = obter_logger("farol.mapa")


def montar_mapa(sessao: Session, relogio: Relogio) -> VisaoDoMapa:
    agora = relogio.agora()
    ultima = ExecucaoRepositorio(sessao).ultima_completa(TipoExecucao.ALERTAS)
    territorios = [
        t
        for t in TerritorioRepositorio(sessao).listar_todos()
        if t.tipo is not TipoTerritorio.NEUTRO
    ]
    postos = PostoRepositorio(sessao).listar_todos()

    dados_obtidos = ultima is not None
    alertas = (
        [alerta_para_nivel(a) for a in AlertaRepositorio(sessao).listar_confirmados_ativos()]
        if dados_obtidos
        else []
    )
    niveis = calcular_niveis(
        [
            TerritorioParaNivel(
                t.codigo, t.soberano_codigo, nomes_para_titulo(t), t.regioes_cobrem_o_pais
            )
            for t in territorios
        ],
        alertas,
        houve_coleta_completa=dados_obtidos,
    )
    _registrar_pendentes_sem_pais(alertas, territorios)

    atualizado_em = ultima.finalizada_em if ultima is not None else None
    return VisaoDoMapa(
        dados_obtidos=dados_obtidos,
        atualizado_em=atualizado_em,
        desatualizado=atualizado_em is not None and agora - atualizado_em > LIMITE_DE_DADOS_ANTIGOS,
        territorios=tuple(
            TerritorioNoMapa(
                codigo=t.codigo,
                nome=t.nome_pt,
                rotulo_busca=t.rotulo_busca or t.nome_pt,
                termos_busca=tuple(t.termos_busca),
                tipo=t.tipo,
                soberano=t.soberano_codigo,
                bandeira=t.codigo_bandeira,
                identidade_do_soberano=t.identidade_do_soberano,
                nivel=niveis[t.codigo].nivel,
                regioes=niveis[t.codigo].regioes_em_destaque,
                observacao=t.observacao,
            )
            for t in territorios
        ),
        postos=tuple(
            PostoNoMapa(
                id=p.id,
                territorio=p.territorio_codigo,
                tipo=p.tipo,
                cidade=p.cidade,
                latitude=float(p.latitude),
                longitude=float(p.longitude),
                grupo=grupo_do_posto(p),
            )
            for p in postos
        ),
        paises_sem_posto=tuple(
            PaisSemPosto(
                territorio=t.codigo,
                latitude=float(t.icone_latitude),
                longitude=float(t.icone_longitude),
                posto_responsavel_id=t.posto_responsavel_id,
            )
            for t in territorios
            if t.icone_latitude is not None and t.icone_longitude is not None
        ),
    )


def _registrar_pendentes_sem_pais(
    alertas: list[AlertaParaNivel], territorios: list[Territorio]
) -> None:
    """Alerta pendente cujo título não cita país nenhum não muda nível algum (risco conhecido):
    fica no log e em `/saude` (alertas pendentes)."""
    pendentes = [a for a in alertas if a.itens is None]
    if not pendentes:
        return
    todos_os_nomes = [n for t in territorios for n in nomes_para_titulo(t)]
    for alerta in pendentes:
        if not titulo_cita(alerta.titulo, todos_os_nomes):
            _log.warning(
                "alerta pendente sem país no título (nenhum nível muda): %r", alerta.titulo
            )
