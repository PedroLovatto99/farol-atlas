"""Agendador do worker: cron diário, coleta na partida, comando de coleta única e encadeamento."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from apscheduler.triggers.cron import CronTrigger

from farol.classificacao import ResultadoDaClassificacao
from farol.coleta import ResultadoDaColeta
from farol.worker import (
    ContatoInvalido,
    ResultadoDaRodada,
    deve_coletar_na_partida,
    executar_comando,
    preparar_agendador,
    rodada_de_alertas,
)

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def coleta(completa: bool = True) -> ResultadoDaColeta:
    return ResultadoDaColeta(
        execucao_id=1,
        completa=completa,
        motivo_interrupcao=None if completa else "caiu na verificação humana",
        paginas_esperadas=18,
        paginas_lidas=18 if completa else 4,
        para_classificar=(1, 2),
        removidos=0,
    )


def rodada_falsa(completa: bool = True, eventos: list[str] | None = None) -> ResultadoDaRodada:
    return ResultadoDaRodada(coleta(completa), ResultadoDaClassificacao(2, 0))


# --------------------------------------------------------------------------- cron diário
def test_coleta_todo_dia_as_0617_no_fuso_de_sao_paulo() -> None:
    agendador = preparar_agendador(
        lambda: None, ultima_tentativa=AGORA, agora=AGORA, limite_horas=20
    )
    [diario] = [j for j in agendador.get_jobs() if j.id == "alertas-diarios"]
    gatilho = diario.trigger
    assert isinstance(gatilho, CronTrigger)
    assert str(gatilho.timezone) == "America/Sao_Paulo"
    campos = {c.name: str(c) for c in gatilho.fields}
    assert (campos["hour"], campos["minute"]) == ("6", "17")
    assert (campos["day"], campos["month"], campos["day_of_week"]) == ("*", "*", "*")


def test_proximas_execucoes_do_cron() -> None:
    agendador = preparar_agendador(
        lambda: None, ultima_tentativa=AGORA, agora=AGORA, limite_horas=20
    )
    [diario] = [j for j in agendador.get_jobs() if j.id == "alertas-diarios"]
    antes = datetime(2026, 10, 23, 5, 0, tzinfo=SAO_PAULO)
    depois = datetime(2026, 10, 23, 7, 0, tzinfo=SAO_PAULO)
    assert diario.trigger.get_next_fire_time(None, antes) == datetime(
        2026, 10, 23, 6, 17, tzinfo=SAO_PAULO
    )
    assert diario.trigger.get_next_fire_time(None, depois) == datetime(
        2026, 10, 24, 6, 17, tzinfo=SAO_PAULO
    )


# --------------------------------------------------------------------------- coleta na partida
@pytest.mark.parametrize(
    ("ultima", "deve"),
    [
        (None, True),  # nunca tentou
        (AGORA - timedelta(hours=21), True),
        (AGORA - timedelta(hours=20, minutes=1), True),
        (AGORA - timedelta(hours=20), False),
        (AGORA - timedelta(hours=3), False),
    ],
    ids=["nunca", "21h", "20h01", "20h-exatas", "3h"],
)
def test_na_partida_so_coleta_se_a_ultima_tentativa_passou_de_20_horas(
    ultima: datetime | None, deve: bool
) -> None:
    assert deve_coletar_na_partida(ultima, AGORA, limite_horas=20) is deve


def test_o_limite_da_partida_e_configuravel() -> None:
    ultima = AGORA - timedelta(hours=5)
    assert deve_coletar_na_partida(ultima, AGORA, limite_horas=4) is True
    assert deve_coletar_na_partida(ultima, AGORA, limite_horas=6) is False


def test_agendador_agenda_a_coleta_da_partida_so_quando_necessario() -> None:
    velho = preparar_agendador(
        lambda: None, ultima_tentativa=AGORA - timedelta(hours=30), agora=AGORA, limite_horas=20
    )
    recente = preparar_agendador(
        lambda: None, ultima_tentativa=AGORA - timedelta(hours=2), agora=AGORA, limite_horas=20
    )
    assert {j.id for j in velho.get_jobs()} == {"alertas-diarios", "alertas-na-partida"}
    assert {j.id for j in recente.get_jobs()} == {"alertas-diarios"}


def test_o_job_agendado_roda_a_rodada_recebida() -> None:
    chamadas: list[str] = []
    agendador = preparar_agendador(
        lambda: chamadas.append("rodou"), ultima_tentativa=None, agora=AGORA, limite_horas=20
    )
    for job in agendador.get_jobs():
        job.func()
    assert chamadas == ["rodou", "rodou"]


# --------------------------------------------------------------------------- coleta → classificação
def test_a_rodada_encadeia_coleta_e_depois_classificacao() -> None:
    eventos: list[str] = []

    def coletar() -> ResultadoDaColeta:
        eventos.append("coleta")
        return coleta()

    def classificar() -> ResultadoDaClassificacao:
        eventos.append("classificacao")
        return ResultadoDaClassificacao(2, 0)

    resultado = rodada_de_alertas(coletar, classificar)

    assert eventos == ["coleta", "classificacao"]
    assert resultado.coleta.completa
    assert resultado.classificacao.classificados == 2


def test_a_classificacao_roda_mesmo_depois_de_coleta_incompleta() -> None:
    eventos: list[str] = []

    def classificar() -> ResultadoDaClassificacao:
        eventos.append("classificacao")
        return ResultadoDaClassificacao(0, 0)

    resultado = rodada_de_alertas(lambda: coleta(completa=False), classificar)
    assert eventos == ["classificacao"]
    assert not resultado.coleta.completa


def test_se_a_coleta_quebrar_nao_classifica_e_o_erro_sobe() -> None:
    eventos: list[str] = []

    def coletar() -> ResultadoDaColeta:
        raise RuntimeError("banco fora do ar")

    def classificar() -> ResultadoDaClassificacao:
        eventos.append("classificacao")
        return ResultadoDaClassificacao(0, 0)

    with pytest.raises(RuntimeError, match="banco fora do ar"):
        rodada_de_alertas(coletar, classificar)
    assert eventos == []


# ------------------------------------------------------------------ comando de coleta única
def test_coletar_alertas_roda_a_rodada_uma_vez(capsys: pytest.CaptureFixture[str]) -> None:
    chamadas: list[int] = []

    def rodada() -> ResultadoDaRodada:
        chamadas.append(1)
        return rodada_falsa()

    codigo = executar_comando(["coletar", "--alertas"], rodada=rodada)

    assert chamadas == [1]
    assert codigo == 0
    saida = capsys.readouterr().out
    assert "18 de 18" in saida  # páginas lidas / esperadas
    assert "completa" in saida


def test_coleta_incompleta_sai_com_codigo_1_e_mostra_o_motivo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = executar_comando(["coletar", "--alertas"], rodada=lambda: rodada_falsa(completa=False))
    assert codigo == 1
    saida = capsys.readouterr().out
    assert "4 de 18" in saida
    assert "caiu na verificação humana" in saida


def test_contato_invalido_vira_mensagem_clara_e_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def rodada() -> ResultadoDaRodada:
        raise ContatoInvalido("defina CONTATO_COLETA no .env")

    codigo = executar_comando(["coletar", "--alertas"], rodada=rodada)

    assert codigo == 2
    assert "defina CONTATO_COLETA" in capsys.readouterr().out


def test_coletar_postos_ainda_nao_existe(capsys: pytest.CaptureFixture[str]) -> None:
    chamadas: list[int] = []

    def rodada() -> ResultadoDaRodada:
        chamadas.append(1)
        return rodada_falsa()

    codigo = executar_comando(["coletar", "--postos"], rodada=rodada)
    assert codigo == 2
    assert chamadas == []
    assert "postos" in capsys.readouterr().out


def test_comando_desconhecido_e_recusado() -> None:
    with pytest.raises(SystemExit) as saida:
        executar_comando(["apagar-tudo"], rodada=rodada_falsa)
    assert saida.value.code == 2
