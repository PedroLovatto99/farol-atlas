"""Ao subir, o worker só coleta vistos sem coleta válida ou com a última válida de mais de 7 dias.

Senão, não agenda coleta nenhuma e portanto não faz requisição: uma tentativa que falhou, foi
adiada ou foi rejeitada não conta. Os testes montam o histórico no banco e leem o agendador que o
worker montaria, sem rodar nenhum job (o que rodar faria a requisição).
"""

from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session

from farol.dominio import ColetaVistos, ResultadoDaColetaDeVistos
from farol.vistos import ProximaTentativa
from farol.worker import preparar_agendador, situacao_de_vistos_na_partida

R = ResultadoDaColetaDeVistos
AGORA = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def tentativa(
    sessao: Session,
    resultado: ResultadoDaColetaDeVistos,
    ha: timedelta,
    *,
    adiamentos: int = 0,
    falhas: int = 0,
) -> None:
    quando = AGORA - ha
    sessao.add(
        ColetaVistos(
            iniciada_em=quando,
            finalizada_em=quando,
            resultado=resultado,
            motivo=None if resultado is R.VALIDA else "motivo qualquer",
            paises_reconhecidos=228 if resultado is R.VALIDA else None,
            adiamentos_seguidos=adiamentos,
            falhas_seguidas=falhas,
        )
    )
    sessao.flush()


def jobs_de_vistos_ao_subir(sessao: Session) -> tuple[set[str], BlockingScheduler]:
    situacao = situacao_de_vistos_na_partida(sessao)
    agendador = preparar_agendador(
        lambda: None,
        ultima_tentativa=AGORA,
        agora=AGORA,
        limite_horas=20,
        rodada_de_vistos=lambda: ProximaTentativa.PROXIMA_SEGUNDA,
        ultima_coleta_valida_de_vistos=situacao.ultima_coleta_valida,
        retomada_de_vistos=situacao.retomada,
    )
    return {j.id for j in agendador.get_jobs() if j.id.startswith("vistos")}, agendador


def test_sem_nenhuma_coleta_coleta_na_partida(sessao: Session) -> None:
    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert ids == {"vistos-semanais", "vistos-na-partida"}


def test_sem_coleta_valida_coleta_na_partida_mesmo_com_tentativa_recente_que_nao_valeu(
    sessao: Session,
) -> None:
    tentativa(sessao, R.REJEITADA, timedelta(hours=2))

    situacao = situacao_de_vistos_na_partida(sessao)
    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert situacao.ultima_coleta_valida is None
    assert ids == {"vistos-semanais", "vistos-na-partida"}


def test_coleta_valida_de_ate_7_dias_nao_gera_coleta_na_partida(sessao: Session) -> None:
    tentativa(sessao, R.VALIDA, timedelta(days=6, hours=23))

    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert ids == {"vistos-semanais"}  # nenhuma coleta ao subir: nenhuma requisição


def test_coleta_valida_de_mais_de_7_dias_coleta_na_partida(sessao: Session) -> None:
    tentativa(sessao, R.VALIDA, timedelta(days=7, minutes=1))

    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert ids == {"vistos-semanais", "vistos-na-partida"}


def test_a_data_que_vale_e_a_da_ultima_coleta_valida_e_nao_a_da_ultima_tentativa(
    sessao: Session,
) -> None:
    tentativa(sessao, R.VALIDA, timedelta(days=9))
    tentativa(sessao, R.BLOQUEADA, timedelta(hours=1))  # a tentativa de agora não conta

    situacao = situacao_de_vistos_na_partida(sessao)
    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert situacao.ultima_coleta_valida == AGORA - timedelta(days=9)
    assert ids == {"vistos-semanais", "vistos-na-partida"}


def test_tentativa_rejeitada_ou_bloqueada_sobre_coleta_valida_recente_nao_coleta_nem_retoma(
    sessao: Session,
) -> None:
    tentativa(sessao, R.VALIDA, timedelta(days=3))
    tentativa(sessao, R.BLOQUEADA, timedelta(days=1))

    situacao = situacao_de_vistos_na_partida(sessao)
    ids, _ = jobs_de_vistos_ao_subir(sessao)

    assert situacao.retomada is None
    assert ids == {"vistos-semanais"}


def test_falha_recente_sobre_coleta_valida_recente_so_marca_a_tentativa_de_amanha(
    sessao: Session,
) -> None:
    tentativa(sessao, R.VALIDA, timedelta(days=2))
    tentativa(sessao, R.FALHOU, timedelta(hours=1), falhas=1)

    situacao = situacao_de_vistos_na_partida(sessao)
    ids, agendador = jobs_de_vistos_ao_subir(sessao)

    assert situacao.retomada is not None
    assert situacao.retomada > AGORA  # 05:13 do dia seguinte: nada roda ao subir
    assert ids == {"vistos-semanais", "vistos-amanha"}
    [amanha] = [j for j in agendador.get_jobs() if j.id == "vistos-amanha"]
    assert amanha.trigger.run_date == situacao.retomada
