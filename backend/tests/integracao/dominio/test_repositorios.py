"""Repositórios: único lugar com SQL. Listas carregam tudo de uma vez (sem N+1)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session

from farol.dominio.enums import (
    NivelAlerta,
    StatusClassificacao,
    TipoExecucao,
    TipoPosto,
    TipoTerritorio,
)
from farol.dominio.modelos import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelTerritorio,
    Posto,
    Territorio,
)
from farol.dominio.repositorios import (
    AlertaRepositorio,
    ExecucaoRepositorio,
    PostoRepositorio,
    TerritorioRepositorio,
)

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas

AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def _hash(n: int) -> str:
    return f"{n:064d}"


def criar_alertas(sessao: Session, quantidade: int) -> ExecucaoColeta:
    """Cria `quantidade` alertas confirmados, cada um com uma classificação ok e dois níveis."""
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=True
    )
    sessao.add(execucao)
    sessao.add_all(
        [
            Territorio(codigo="AA", nome_pt="Aaa", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="BB", nome_pt="Bbb", tipo=TipoTerritorio.PAIS),
        ]
    )
    sessao.flush()
    for n in range(quantidade):
        alerta = Alerta(
            url=f"https://gov.br/alerta-{n}",
            titulo=f"Alerta {n}",
            publicado_em=AGORA,
            primeira_coleta_em=AGORA,
            ultima_coleta_em=AGORA,
            hash=_hash(n),
            confirmado_execucao_id=execucao.id,
            confirmado_hash=_hash(n),
            confirmado_titulo=f"Alerta {n}",
            confirmado_data_ref=AGORA,
        )
        sessao.add(alerta)
        sessao.flush()
        classificacao = Classificacao(
            alerta_id=alerta.id,
            alerta_hash=_hash(n),
            status=StatusClassificacao.OK,
            e_alerta_de_viagem=True,
            modelo="modelo-falso",
            classificado_em=AGORA,
        )
        sessao.add(classificacao)
        sessao.flush()
        sessao.add_all(
            [
                NivelTerritorio(
                    classificacao_id=classificacao.id,
                    territorio_codigo=codigo,
                    nivel_pais=NivelAlerta.EVITAR,
                )
                for codigo in ("AA", "BB")
            ]
        )
    sessao.flush()
    sessao.expire_all()
    return execucao


@pytest.mark.parametrize("quantidade", [3, 30])
def test_alertas_confirmados_carregam_tudo_em_consultas_fixas(
    sessao: Session, contar_consultas: "ContadorDeConsultas", quantidade: int
) -> None:
    criar_alertas(sessao, quantidade)
    repositorio = AlertaRepositorio(sessao)
    with contar_consultas as contador:
        alertas = repositorio.listar_confirmados_ativos()
        niveis = [
            n for a in alertas if (c := a.classificacao_vigente()) is not None for n in c.niveis
        ]
    assert len(alertas) == quantidade
    assert len(niveis) == quantidade * 2
    # Alertas + classificações + níveis: o mesmo número de consultas com 3 ou com 30 alertas
    assert contador.total == 3


def test_alerta_nao_confirmado_ou_removido_fica_de_fora(sessao: Session) -> None:
    criar_alertas(sessao, 2)
    sessao.add(
        Alerta(
            url="https://gov.br/novo",
            titulo="Lido só numa coleta incompleta",
            publicado_em=AGORA,
            primeira_coleta_em=AGORA,
            ultima_coleta_em=AGORA,
        )
    )
    removido = sessao.query(Alerta).filter_by(url="https://gov.br/alerta-0").one()
    removido.removido_em = AGORA
    sessao.flush()

    urls = {a.url for a in AlertaRepositorio(sessao).listar_confirmados_ativos()}

    assert urls == {"https://gov.br/alerta-1"}


def test_classificacao_vigente_exige_o_hash_confirmado(sessao: Session) -> None:
    criar_alertas(sessao, 1)
    alerta = sessao.query(Alerta).one()
    assert alerta.classificacao_vigente() is not None
    alerta.confirmado_hash = _hash(99)  # conteúdo confirmado ainda sem classificação
    sessao.flush()
    sessao.expire(alerta, ["classificacoes"])
    assert alerta.classificacao_vigente() is None


def test_ultima_execucao_completa_ignora_as_incompletas_e_o_outro_tipo(sessao: Session) -> None:
    def execucao(tipo: TipoExecucao, dias: int, completa: bool) -> ExecucaoColeta:
        fim = AGORA - timedelta(days=dias)
        return ExecucaoColeta(tipo=tipo, iniciada_em=fim, finalizada_em=fim, completa=completa)

    antiga = execucao(TipoExecucao.ALERTAS, 5, True)
    recente_completa = execucao(TipoExecucao.ALERTAS, 2, True)
    mais_recente_incompleta = execucao(TipoExecucao.ALERTAS, 0, False)
    de_postos = execucao(TipoExecucao.POSTOS, 1, True)
    sessao.add_all([antiga, recente_completa, mais_recente_incompleta, de_postos])
    sessao.flush()

    repositorio = ExecucaoRepositorio(sessao)

    assert repositorio.ultima_completa(TipoExecucao.ALERTAS) == recente_completa
    assert repositorio.ultima_tentativa(TipoExecucao.ALERTAS) == mais_recente_incompleta
    assert repositorio.ultima_completa(TipoExecucao.POSTOS) == de_postos


def test_ultima_execucao_completa_sem_nenhuma_devolve_none(sessao: Session) -> None:
    assert ExecucaoRepositorio(sessao).ultima_completa(TipoExecucao.ALERTAS) is None
    assert ExecucaoRepositorio(sessao).ultima_tentativa(TipoExecucao.ALERTAS) is None


def test_territorios_e_postos_em_uma_consulta_cada(
    sessao: Session, contar_consultas: "ContadorDeConsultas"
) -> None:
    sessao.add(Territorio(codigo="PT", nome_pt="Portugal", tipo=TipoTerritorio.PAIS))
    sessao.flush()
    for n in range(1, 11):
        sessao.add(
            Posto(
                id=n,
                territorio_codigo="PT",
                cidade=f"Cidade {n}",
                tipo=TipoPosto.CONSULADO,
                latitude=Decimal("38.72000"),
                longitude=Decimal("-9.14000"),
            )
        )
    sessao.flush()
    sessao.expire_all()

    with contar_consultas as contador:
        territorios = TerritorioRepositorio(sessao).listar_todos()
        postos = PostoRepositorio(sessao).listar_todos()
    assert [t.codigo for t in territorios] == ["PT"]
    assert len(postos) == 10
    assert contador.total == 2


def test_postos_de_um_territorio(sessao: Session) -> None:
    sessao.add_all(
        [
            Territorio(codigo="PT", nome_pt="Portugal", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="ES", nome_pt="Espanha", tipo=TipoTerritorio.PAIS),
        ]
    )
    sessao.flush()
    for n, codigo in enumerate(["PT", "PT", "ES"], start=1):
        sessao.add(
            Posto(
                id=n,
                territorio_codigo=codigo,
                cidade=f"Cidade {n}",
                tipo=TipoPosto.EMBAIXADA,
                latitude=Decimal("1.00000"),
                longitude=Decimal("1.00000"),
            )
        )
    sessao.flush()

    postos = PostoRepositorio(sessao).listar_por_territorio("PT")

    assert [p.id for p in postos] == [1, 2]


def test_codigos_permitidos_para_o_classificador(sessao: Session) -> None:
    sessao.add_all(
        [
            Territorio(codigo="PT", nome_pt="Portugal", tipo=TipoTerritorio.PAIS),
            Territorio(
                codigo="GL",
                nome_pt="Groenlândia (Dinamarca)",
                tipo=TipoTerritorio.DEPENDENCIA,
                soberano_codigo="PT",
            ),
            Territorio(codigo="AQ", nome_pt="Antártida", tipo=TipoTerritorio.NEUTRO),
        ]
    )
    sessao.flush()

    assert TerritorioRepositorio(sessao).codigos_com_nivel() == {"PT", "GL"}


def test_territorio_e_soberano_vem_numa_consulta_so(
    sessao: Session, contar_consultas: "ContadorDeConsultas"
) -> None:
    sessao.add_all(
        [
            Territorio(codigo="PT", nome_pt="Portugal", tipo=TipoTerritorio.PAIS),
            Territorio(codigo="ES", nome_pt="Espanha", tipo=TipoTerritorio.PAIS),
            Territorio(
                codigo="GL",
                nome_pt="Groenlândia (Dinamarca)",
                tipo=TipoTerritorio.DEPENDENCIA,
                soberano_codigo="PT",
            ),
        ]
    )
    sessao.flush()
    repositorio = TerritorioRepositorio(sessao)

    with contar_consultas as contador:
        dependencia = repositorio.obter_com_soberano("GL")
        pais = repositorio.obter_com_soberano("ES")
        desconhecido = repositorio.obter_com_soberano("ZZ")

    assert [t.codigo for t in dependencia] == ["GL", "PT"]  # o território e o soberano dele
    assert [t.codigo for t in pais] == ["ES"]  # sem soberano: só ele
    assert desconhecido == []
    assert contador.total == 3
