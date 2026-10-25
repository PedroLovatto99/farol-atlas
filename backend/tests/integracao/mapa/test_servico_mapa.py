"""Serviço do mapa: monta a visão de `/mapa` com número fixo de consultas (princípio III)."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelAlerta,
    NivelTerritorio,
    Posto,
    StatusClassificacao,
    Territorio,
    TipoExecucao,
    TipoTerritorio,
)
from farol.dominio.seed import executar
from farol.mapa import NivelExibido, VisaoDoMapa, montar_mapa

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas, RelogioFalso

DADOS = Path(__file__).resolve().parents[4] / "dados"
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)

Item = tuple[str, NivelAlerta | None, list[tuple[str, NivelAlerta]]]


@pytest.fixture
def semeado(sessao: Session) -> Session:
    executar(sessao, DADOS, AGORA)
    return sessao


def execucao_completa(sessao: Session, finalizada_em: datetime) -> ExecucaoColeta:
    execucao = ExecucaoColeta(
        tipo=TipoExecucao.ALERTAS,
        iniciada_em=finalizada_em - timedelta(minutes=5),
        finalizada_em=finalizada_em,
        paginas_esperadas=10,
        paginas_lidas=10,
        lista_lida_inteira=True,
        completa=True,
    )
    sessao.add(execucao)
    sessao.flush()
    return execucao


def criar_alerta(
    sessao: Session,
    execucao: ExecucaoColeta,
    numero: int,
    titulo: str,
    data_ref: datetime,
    itens: list[Item] | None,
    *,
    publicado_em: datetime | None = None,
    removido: bool = False,
    status: StatusClassificacao = StatusClassificacao.OK,
    hash_classificado: str | None = None,
) -> Alerta:
    """Alerta confirmado. `itens=None` = sem classificação (pendente); `[]` = não é de viagem."""
    hash_do_alerta = f"{numero:064d}"
    alerta = Alerta(
        url=f"https://www.gov.br/mre/alerta-{numero}",
        titulo=titulo,
        texto="texto",
        publicado_em=publicado_em or data_ref,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
        hash=hash_do_alerta,
        removido_em=AGORA if removido else None,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_do_alerta,
        confirmado_titulo=titulo,
        confirmado_data_ref=data_ref,
    )
    sessao.add(alerta)
    sessao.flush()
    if itens is not None or status is StatusClassificacao.FALHOU:
        classificacao = Classificacao(
            alerta_id=alerta.id,
            alerta_hash=hash_classificado or hash_do_alerta,
            status=status,
            e_alerta_de_viagem=None if status is StatusClassificacao.FALHOU else bool(itens),
            modelo="modelo-falso",
            erro="falhou" if status is StatusClassificacao.FALHOU else None,
            classificado_em=AGORA,
        )
        sessao.add(classificacao)
        sessao.flush()
        for codigo, nivel, regioes in itens or []:
            sessao.add(
                NivelTerritorio(
                    classificacao_id=classificacao.id,
                    territorio_codigo=codigo,
                    nivel_pais=nivel,
                    regioes=[{"nome": nome, "nivel": n.value} for nome, n in regioes],
                )
            )
        sessao.flush()
    return alerta


def por_codigo(visao: VisaoDoMapa) -> dict[str, Any]:
    return {t.codigo: t for t in visao.territorios}


# --------------------------------------------------------------------------- sem coleta
def test_sem_coleta_completa_nada_foi_obtido_e_tudo_e_nao_verificado(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    visao = montar_mapa(semeado, relogio)
    assert visao.dados_obtidos is False
    assert visao.atualizado_em is None
    assert visao.desatualizado is False
    assert {t.nivel for t in visao.territorios} == {NivelExibido.NAO_VERIFICADO}


def test_coleta_incompleta_nao_conta_como_dados_obtidos(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    semeado.add(
        ExecucaoColeta(
            tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, finalizada_em=AGORA, completa=False
        )
    )
    semeado.flush()
    assert montar_mapa(semeado, relogio).dados_obtidos is False


# --------------------------------------------------------------------------- níveis
def test_niveis_do_roteiro_de_validacao(semeado: Session, relogio: "RelogioFalso") -> None:
    execucao = execucao_completa(semeado, AGORA - timedelta(hours=6))
    E, N, NORM = NivelAlerta.EVITAR, NivelAlerta.NAO_VIAJAR, NivelAlerta.NORMALIZADA
    # Bolívia: o alerta antigo era "não viaje", o mais recente informa a normalização
    criar_alerta(
        semeado, execucao, 1, "Bolívia (antigo)", datetime(2026, 3, 1, tzinfo=UTC), [("BO", N, [])]
    )
    criar_alerta(
        semeado,
        execucao,
        2,
        "Alerta de viagem – Bolívia",
        datetime(2026, 7, 10, tzinfo=UTC),
        [("BO", NORM, [])],
    )
    # Oriente Médio
    criar_alerta(
        semeado, execucao, 3, "Alerta Consular. Oriente Médio.", datetime(2026, 8, 17, tzinfo=UTC),
        [
            ("IR", N, []),
            ("LB", E, [("Sul do Líbano", N)]),
            ("SY", None, [("Norte da Síria", N)]),
        ],
    )  # fmt: skip
    # fraude: não é alerta de viagem
    criar_alerta(
        semeado, execucao, 4, "Alerta de fraudes nos EUA", datetime(2026, 9, 1, tzinfo=UTC), []
    )

    visao = montar_mapa(semeado, relogio)
    territorios = por_codigo(visao)

    assert visao.dados_obtidos is True
    assert territorios["BO"].nivel is NivelExibido.SEM_ALERTA
    assert territorios["IR"].nivel is NivelExibido.NAO_VIAJAR
    assert territorios["LB"].nivel is NivelExibido.EVITAR
    assert [(r.nome, r.nivel.value) for r in territorios["LB"].regioes] == [
        ("Sul do Líbano", "nao_viajar")
    ]
    assert territorios["SY"].nivel is NivelExibido.SEM_ALERTA
    assert [r.nome for r in territorios["SY"].regioes] == ["Norte da Síria"]
    assert territorios["US"].nivel is NivelExibido.SEM_ALERTA  # a fraude não conta
    assert territorios["FR"].nivel is NivelExibido.SEM_ALERTA


def test_vale_a_data_de_referencia_confirmada_e_nao_a_de_publicacao(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    E, N = NivelAlerta.EVITAR, NivelAlerta.NAO_VIAJAR
    # publicado em junho, mas modificado em setembro: é o mais recente
    criar_alerta(
        semeado, execucao, 1, "Israel", datetime(2026, 9, 1, tzinfo=UTC), [("IL", N, [])],
        publicado_em=datetime(2026, 6, 1, tzinfo=UTC),
    )  # fmt: skip
    criar_alerta(semeado, execucao, 2, "Israel", datetime(2026, 8, 1, tzinfo=UTC), [("IL", E, [])])
    assert por_codigo(montar_mapa(semeado, relogio))["IL"].nivel is NivelExibido.NAO_VIAJAR


def test_dependencias_seguem_o_soberano_e_kosovo_segue_a_servia(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    criar_alerta(
        semeado,
        execucao,
        1,
        "Dinamarca",
        datetime(2026, 5, 1, tzinfo=UTC),
        [("DK", NivelAlerta.EVITAR, [])],
    )
    criar_alerta(
        semeado,
        execucao,
        2,
        "Sérvia",
        datetime(2026, 5, 1, tzinfo=UTC),
        [("RS", NivelAlerta.NAO_VIAJAR, [])],
    )
    territorios = por_codigo(montar_mapa(semeado, relogio))
    assert territorios["GL"].nivel is NivelExibido.EVITAR
    assert territorios["XK"].nivel is NivelExibido.NAO_VIAJAR


def test_alerta_removido_ou_nao_confirmado_nao_vale(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    criar_alerta(
        semeado,
        execucao,
        1,
        "Peru",
        datetime(2026, 5, 1, tzinfo=UTC),
        [("PE", NivelAlerta.NAO_VIAJAR, [])],
        removido=True,
    )
    lido_mas_nao_confirmado = criar_alerta(
        semeado,
        execucao,
        2,
        "Chile",
        datetime(2026, 5, 1, tzinfo=UTC),
        [("CL", NivelAlerta.NAO_VIAJAR, [])],
    )
    lido_mas_nao_confirmado.confirmado_execucao_id = None
    semeado.flush()
    territorios = por_codigo(montar_mapa(semeado, relogio))
    assert territorios["PE"].nivel is NivelExibido.SEM_ALERTA
    assert territorios["CL"].nivel is NivelExibido.SEM_ALERTA


# --------------------------------------------------------------------------- pendentes
def test_alerta_pendente_com_pais_no_titulo_deixa_o_pais_nao_verificado(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    criar_alerta(
        semeado, execucao, 1, "Alerta de viagem – Peru", datetime(2026, 9, 1, tzinfo=UTC), None
    )
    territorios = por_codigo(montar_mapa(semeado, relogio))
    assert territorios["PE"].nivel is NivelExibido.NAO_VERIFICADO
    assert territorios["BO"].nivel is NivelExibido.SEM_ALERTA


def test_classificacao_que_falhou_ou_de_outro_hash_deixa_o_alerta_pendente(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    criar_alerta(
        semeado, execucao, 1, "Alerta de viagem – Peru", datetime(2026, 9, 1, tzinfo=UTC), None,
        status=StatusClassificacao.FALHOU,
    )  # fmt: skip
    criar_alerta(
        semeado, execucao, 2, "Alerta de viagem – Chile", datetime(2026, 9, 1, tzinfo=UTC),
        [("CL", NivelAlerta.NORMALIZADA, [])], hash_classificado="f" * 64,
    )  # fmt: skip
    territorios = por_codigo(montar_mapa(semeado, relogio))
    assert territorios["PE"].nivel is NivelExibido.NAO_VERIFICADO
    assert territorios["CL"].nivel is NivelExibido.NAO_VERIFICADO


def test_registra_no_log_o_alerta_pendente_que_nao_cita_nenhum_pais(
    semeado: Session, relogio: "RelogioFalso", caplog: pytest.LogCaptureFixture
) -> None:
    execucao = execucao_completa(semeado, AGORA)
    criar_alerta(
        semeado,
        execucao,
        1,
        "Alerta Consular. Oriente Médio.",
        datetime(2026, 9, 1, tzinfo=UTC),
        None,
    )
    criar_alerta(
        semeado, execucao, 2, "Alerta de viagem – Peru", datetime(2026, 9, 2, tzinfo=UTC), None
    )

    with caplog.at_level(logging.WARNING, logger="farol.mapa"):
        visao = montar_mapa(semeado, relogio)

    mensagens = [r.getMessage() for r in caplog.records if r.name == "farol.mapa"]
    assert any("Oriente Médio" in m for m in mensagens)
    assert not any("Peru" in m for m in mensagens)  # esse cita um país
    assert por_codigo(visao)["PE"].nivel is NivelExibido.NAO_VERIFICADO


# --------------------------------------------------------------------------- atualização
@pytest.mark.parametrize(
    ("idade", "desatualizado"),
    [
        (timedelta(hours=6), False),
        (timedelta(days=3), False),
        (timedelta(days=3, minutes=1), True),
        (timedelta(days=10), True),
    ],
)
def test_dados_desatualizados_depois_de_tres_dias(
    semeado: Session, relogio: "RelogioFalso", idade: timedelta, desatualizado: bool
) -> None:
    finalizada = relogio.agora() - idade
    execucao_completa(semeado, finalizada)
    visao = montar_mapa(semeado, relogio)
    assert visao.atualizado_em == finalizada
    assert visao.desatualizado is desatualizado


def test_mostra_a_ultima_coleta_completa_mesmo_com_tentativas_recentes_incompletas(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    completa = execucao_completa(semeado, relogio.agora() - timedelta(days=1))
    semeado.add(
        ExecucaoColeta(
            tipo=TipoExecucao.ALERTAS,
            iniciada_em=relogio.agora() - timedelta(hours=1),
            finalizada_em=relogio.agora() - timedelta(minutes=50),
            completa=False,
            motivo_interrupcao="caiu na verificação humana",
        )
    )
    semeado.flush()
    assert montar_mapa(semeado, relogio).atualizado_em == completa.finalizada_em


# --------------------------------------------------------------------------- territórios
def test_territorios_com_identidade_do_soberano_e_busca(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    territorios = por_codigo(montar_mapa(semeado, relogio))

    kosovo = territorios["XK"]
    assert kosovo.tipo is TipoTerritorio.DEPENDENCIA
    assert kosovo.soberano == "RS"
    assert kosovo.bandeira == "RS"
    assert kosovo.identidade_do_soberano is True
    assert kosovo.nome == "Sérvia"
    assert kosovo.rotulo_busca == "Kosovo (Sérvia)"
    assert kosovo.termos_busca == ("Kosovo",)
    assert kosovo.observacao is not None

    malvinas = territorios["FK"]
    assert (malvinas.bandeira, malvinas.soberano) == ("AR", "AR")
    assert malvinas.termos_busca == ("Malvinas", "Ilhas Malvinas")

    groenlandia = territorios["GL"]
    assert groenlandia.nome == "Groenlândia (Dinamarca)"
    assert groenlandia.rotulo_busca == "Groenlândia (Dinamarca)"  # sem rótulo próprio: o nome
    assert groenlandia.bandeira == "GL"
    assert groenlandia.termos_busca == ()

    assert territorios["TW"].bandeira is None
    assert territorios["BR"].tipo is TipoTerritorio.PAIS
    assert territorios["BR"].soberano is None


def test_todos_os_198_paises_da_lista_estao_na_visao(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    lista = set(
        semeado.scalars(select(Territorio.codigo).where(Territorio.na_lista_itamaraty.is_(True)))
    )
    assert len(lista) == 198
    assert lista <= set(por_codigo(montar_mapa(semeado, relogio)))


# --------------------------------------------------------------------------- postos
def test_postos_na_mesma_coordenada_dividem_o_grupo(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    visao = montar_mapa(semeado, relogio)
    postos = {p.id: p for p in visao.postos}
    # Washington: embaixada (89) e consulado-geral (90) na mesma coordenada
    assert postos[89].grupo == postos[90].grupo
    assert postos[89].cidade == "Washington"
    assert postos[89].territorio == "US"
    assert postos[91].grupo != postos[89].grupo  # Atlanta
    assert (postos[89].latitude, postos[89].longitude) == (38.9047, -77.0164)


def test_todo_pais_com_posto_traz_ao_menos_um_posto(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    com_posto = set(semeado.scalars(select(Posto.territorio_codigo)))
    na_visao = {p.territorio for p in montar_mapa(semeado, relogio).postos}
    assert com_posto == na_visao
    assert len(montar_mapa(semeado, relogio).postos) == 209  # SC-006


def test_paises_sem_posto_trazem_o_ponto_do_icone_e_o_responsavel(
    semeado: Session, relogio: "RelogioFalso"
) -> None:
    visao = montar_mapa(semeado, relogio)
    sem_posto = {p.territorio: p for p in visao.paises_sem_posto}
    assert len(sem_posto) == 60

    libia = sem_posto["LY"]
    assert libia.posto_responsavel_id is None  # sem posto indicado (FR-014)
    assert -90 <= libia.latitude <= 90

    porto_rico = sem_posto["PR"]
    responsavel = semeado.get(Posto, porto_rico.posto_responsavel_id)
    assert responsavel is not None
    assert responsavel.cidade == "Miami"

    assert "US" not in sem_posto  # país com posto não tem ícone de "sem posto"


# --------------------------------------------------------------------------- consultas
def test_numero_de_consultas_nao_depende_dos_dados(
    semeado: Session, relogio: "RelogioFalso", contar_consultas: "ContadorDeConsultas"
) -> None:
    execucao = execucao_completa(semeado, AGORA)

    def criar(de: int, ate: int) -> None:
        for n in range(de, ate):
            criar_alerta(
                semeado,
                execucao,
                n,
                f"Alerta {n}",
                datetime(2026, 5, 1, tzinfo=UTC) + timedelta(days=n),
                [
                    ("BO", NivelAlerta.EVITAR, [("Região", NivelAlerta.NAO_VIAJAR)]),
                    ("PE", NivelAlerta.EVITAR, []),
                ],
            )

    criar(0, 3)
    with contar_consultas as contador:
        montar_mapa(semeado, relogio)
    com_poucos = contador.total
    criar(3, 60)
    with contar_consultas as contador:
        montar_mapa(semeado, relogio)
    com_muitos = contador.total

    assert com_muitos == com_poucos
    assert com_muitos <= 6
