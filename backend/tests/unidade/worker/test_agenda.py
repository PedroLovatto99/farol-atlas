"""Agendador do worker: cron diário e mensal, coleta na partida, comandos de coleta única."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from apscheduler.triggers.cron import CronTrigger

from farol.classificacao import (
    AlertaNaoEncontrado,
    ResultadoDaClassificacao,
    ResultadoDaReclassificacao,
)
from farol.coleta import ResultadoDaColeta, ResultadoDaColetaDePostos
from farol.worker import (
    ClassificadorIndisponivel,
    ContatoInvalido,
    ResultadoDaRodada,
    deve_coletar_na_partida,
    deve_coletar_postos_na_partida,
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


def coleta_de_postos(completa: bool = True) -> ResultadoDaColetaDePostos:
    return ResultadoDaColetaDePostos(
        execucao_id=2,
        completa=completa,
        motivo_interrupcao=None if completa else "bloqueado (HTTP 429)",
        paginas_esperadas=150,
        paginas_lidas=150 if completa else 12,
        postos_com_endereco=40,
        postos_com_telefone=25,
    )


def sem_postos() -> ResultadoDaColetaDePostos:
    raise AssertionError("a coleta de postos não devia rodar")


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

    codigo = executar_comando(["coletar", "--alertas"], rodada=rodada, rodada_de_postos=sem_postos)

    assert chamadas == [1]
    assert codigo == 0
    saida = capsys.readouterr().out
    assert "18 de 18" in saida  # páginas lidas / esperadas
    assert "completa" in saida


def test_coleta_incompleta_sai_com_codigo_1_e_mostra_o_motivo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = executar_comando(
        ["coletar", "--alertas"],
        rodada=lambda: rodada_falsa(completa=False),
        rodada_de_postos=sem_postos,
    )
    assert codigo == 1
    saida = capsys.readouterr().out
    assert "4 de 18" in saida
    assert "caiu na verificação humana" in saida


def test_contato_invalido_vira_mensagem_clara_e_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def rodada() -> ResultadoDaRodada:
        raise ContatoInvalido("defina CONTATO_COLETA no .env")

    codigo = executar_comando(["coletar", "--alertas"], rodada=rodada, rodada_de_postos=sem_postos)

    assert codigo == 2
    assert "defina CONTATO_COLETA" in capsys.readouterr().out


def test_coletar_postos_roda_so_a_coleta_de_postos(capsys: pytest.CaptureFixture[str]) -> None:
    chamadas: list[str] = []

    def alertas() -> ResultadoDaRodada:
        chamadas.append("alertas")
        return rodada_falsa()

    def postos() -> ResultadoDaColetaDePostos:
        chamadas.append("postos")
        return coleta_de_postos()

    codigo = executar_comando(["coletar", "--postos"], rodada=alertas, rodada_de_postos=postos)

    assert codigo == 0
    assert chamadas == ["postos"]
    saida = capsys.readouterr().out
    assert "completa" in saida
    assert "150 de 150" in saida
    assert "com endereço: 40" in saida
    assert "com telefone: 25" in saida


def test_coleta_de_postos_incompleta_sai_com_codigo_1_e_mostra_o_motivo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = executar_comando(
        ["coletar", "--postos"],
        rodada=rodada_falsa,
        rodada_de_postos=lambda: coleta_de_postos(completa=False),
    )
    assert codigo == 1
    saida = capsys.readouterr().out
    assert "INCOMPLETA" in saida
    assert "12 de 150" in saida
    assert "bloqueado (HTTP 429)" in saida


def test_coleta_de_postos_sem_contato_valido_vira_mensagem_clara_e_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def postos() -> ResultadoDaColetaDePostos:
        raise ContatoInvalido("defina CONTATO_COLETA no .env")

    codigo = executar_comando(["coletar", "--postos"], rodada=rodada_falsa, rodada_de_postos=postos)

    assert codigo == 2
    assert "defina CONTATO_COLETA" in capsys.readouterr().out


def test_comando_desconhecido_e_recusado() -> None:
    with pytest.raises(SystemExit) as saida:
        executar_comando(["apagar-tudo"], rodada=rodada_falsa, rodada_de_postos=sem_postos)
    assert saida.value.code == 2


# --------------------------------------------------------------------------- reclassificar
def reclassificada(ok: bool = True) -> ResultadoDaReclassificacao:
    return ResultadoDaReclassificacao(
        alerta_id=2,
        url="https://www.gov.br/mre/oriente-medio",
        titulo="Alerta Consular. Oriente Médio.",
        ok=ok,
        motivo=None if ok else "RespostaInvalida: código 'ZZ' não existe no mapa",
    )


def test_reclassificar_passa_a_referencia_para_o_servico_e_sai_com_0(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recebidas: list[str] = []

    def reclassificar(referencia: str) -> ResultadoDaReclassificacao:
        recebidas.append(referencia)
        return reclassificada()

    codigo = executar_comando(
        ["reclassificar", "https://www.gov.br/mre/oriente-medio"],
        rodada=rodada_falsa,
        rodada_de_postos=sem_postos,
        reclassificar=reclassificar,
    )

    assert codigo == 0
    assert recebidas == ["https://www.gov.br/mre/oriente-medio"]
    saida = capsys.readouterr().out
    assert "Alerta 2" in saida
    assert "reclassificado" in saida


def test_reclassificar_que_falha_mostra_o_motivo_e_sai_com_1(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = executar_comando(
        ["reclassificar", "2"],
        rodada=rodada_falsa,
        rodada_de_postos=sem_postos,
        reclassificar=lambda referencia: reclassificada(ok=False),
    )

    assert codigo == 1
    saida = capsys.readouterr().out
    assert "NÃO reclassificado" in saida
    assert "'ZZ'" in saida


def test_reclassificar_alerta_inexistente_sai_com_2(capsys: pytest.CaptureFixture[str]) -> None:
    def reclassificar(referencia: str) -> ResultadoDaReclassificacao:
        raise AlertaNaoEncontrado(referencia)

    codigo = executar_comando(
        ["reclassificar", "999"],
        rodada=rodada_falsa,
        rodada_de_postos=sem_postos,
        reclassificar=reclassificar,
    )

    assert codigo == 2
    assert "999" in capsys.readouterr().out


def test_reclassificar_sem_modelo_configurado_vira_mensagem_clara_e_codigo_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def reclassificar(referencia: str) -> ResultadoDaReclassificacao:
        raise ClassificadorIndisponivel("falta GOOGLE_API_KEY")

    codigo = executar_comando(
        ["reclassificar", "2"],
        rodada=rodada_falsa,
        rodada_de_postos=sem_postos,
        reclassificar=reclassificar,
    )

    assert codigo == 2
    assert "falta GOOGLE_API_KEY" in capsys.readouterr().out


def test_reclassificar_sem_alerta_e_recusado() -> None:
    with pytest.raises(SystemExit) as saida:
        executar_comando(["reclassificar"], rodada=rodada_falsa, rodada_de_postos=sem_postos)
    assert saida.value.code == 2


def test_reclassificar_nao_dispara_nenhuma_coleta() -> None:
    codigo = executar_comando(
        ["reclassificar", "2"],
        rodada=lambda: (_ for _ in ()).throw(AssertionError("não devia coletar alertas")),
        rodada_de_postos=sem_postos,
        reclassificar=lambda referencia: reclassificada(),
    )
    assert codigo == 0


# --------------------------------------------------------------------------- postos (mensal)
def test_coleta_de_postos_todo_dia_1_no_fuso_de_sao_paulo() -> None:
    agendador = preparar_agendador(
        lambda: None,
        ultima_tentativa=AGORA,
        agora=AGORA,
        limite_horas=20,
        rodada_de_postos=lambda: None,
        ultima_tentativa_de_postos=AGORA,
    )
    [mensal] = [j for j in agendador.get_jobs() if j.id == "postos-mensais"]
    gatilho = mensal.trigger
    assert isinstance(gatilho, CronTrigger)
    assert str(gatilho.timezone) == "America/Sao_Paulo"
    campos = {c.name: str(c) for c in gatilho.fields}
    assert (campos["day"], campos["month"], campos["day_of_week"]) == ("1", "*", "*")
    assert (campos["hour"], campos["minute"]) == ("5", "43")


def test_proxima_execucao_do_cron_mensal() -> None:
    agendador = preparar_agendador(
        lambda: None,
        ultima_tentativa=AGORA,
        agora=AGORA,
        limite_horas=20,
        rodada_de_postos=lambda: None,
        ultima_tentativa_de_postos=AGORA,
    )
    [mensal] = [j for j in agendador.get_jobs() if j.id == "postos-mensais"]
    meio_do_mes = datetime(2026, 10, 23, 12, 0, tzinfo=SAO_PAULO)
    assert mensal.trigger.get_next_fire_time(None, meio_do_mes) == datetime(
        2026, 11, 1, 5, 43, tzinfo=SAO_PAULO
    )


@pytest.mark.parametrize(
    ("ultima", "deve"),
    [
        (None, True),
        (AGORA - timedelta(days=36), True),
        (AGORA - timedelta(days=35, minutes=1), True),
        (AGORA - timedelta(days=35), False),
        (AGORA - timedelta(days=3), False),
    ],
    ids=["nunca", "36d", "35d1min", "35d-exatos", "3d"],
)
def test_na_partida_so_coleta_postos_se_a_ultima_tentativa_passou_de_35_dias(
    ultima: datetime | None, deve: bool
) -> None:
    assert deve_coletar_postos_na_partida(ultima, AGORA, limite_dias=35) is deve


def test_agendador_agenda_postos_na_partida_so_quando_necessario() -> None:
    def ids(ultima: datetime | None) -> set[str]:
        agendador = preparar_agendador(
            lambda: None,
            ultima_tentativa=AGORA,
            agora=AGORA,
            limite_horas=20,
            rodada_de_postos=lambda: None,
            ultima_tentativa_de_postos=ultima,
        )
        return {j.id for j in agendador.get_jobs()}

    com_partida = {"alertas-diarios", "postos-mensais", "postos-na-partida"}
    assert ids(None) == com_partida
    assert ids(AGORA - timedelta(days=40)) == com_partida
    assert ids(AGORA - timedelta(days=10)) == {"alertas-diarios", "postos-mensais"}


def test_sem_rodada_de_postos_so_ha_os_jobs_de_alertas() -> None:
    agendador = preparar_agendador(
        lambda: None, ultima_tentativa=None, agora=AGORA, limite_horas=20
    )
    assert {j.id for j in agendador.get_jobs()} == {"alertas-diarios", "alertas-na-partida"}


def test_cada_job_roda_a_sua_rodada() -> None:
    chamadas: list[str] = []
    agendador = preparar_agendador(
        lambda: chamadas.append("alertas"),
        ultima_tentativa=None,
        agora=AGORA,
        limite_horas=20,
        rodada_de_postos=lambda: chamadas.append("postos"),
        ultima_tentativa_de_postos=None,
    )
    for job in agendador.get_jobs():
        job.func()
    assert sorted(chamadas) == ["alertas", "alertas", "postos", "postos"]


def test_na_partida_os_alertas_vem_antes_dos_postos() -> None:
    agendador = preparar_agendador(
        lambda: None,
        ultima_tentativa=None,
        agora=AGORA,
        limite_horas=20,
        rodada_de_postos=lambda: None,
        ultima_tentativa_de_postos=None,
    )
    ordem = [j.id for j in agendador.get_jobs() if j.id.endswith("na-partida")]
    assert ordem == ["alertas-na-partida", "postos-na-partida"]
