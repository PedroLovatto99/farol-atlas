"""Agendamento do worker (D5): coleta diária às 06:17 de Brasília e coleta na partida.

Na partida, o worker coleta logo se a última TENTATIVA tiver mais de `limite_horas` (padrão 20 h),
para um servidor reiniciado não esperar até o dia seguinte. Uma falha recente não é repetida antes
do dia seguinte: a spec tolera até 3 dias sem coleta completa.

A coleta de postos (endereço e telefone) é mensal: dia 1, às 05:43. Na partida, só roda se a última
tentativa tiver mais de 35 dias, para uma instalação nova não ficar um mês sem contatos.

Os jobs rodam um de cada vez (um só fio de execução): o gov.br recebe uma requisição por vez, com
a pausa do cliente educado, mesmo quando a coleta de postos cai junto da de alertas.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from farol.infra import FUSO_DE_BRASILIA

HORA_DA_COLETA = 6
MINUTO_DA_COLETA = 17
HORA_DA_COLETA_DE_POSTOS = 5
MINUTO_DA_COLETA_DE_POSTOS = 43
LIMITE_DIAS_DE_POSTOS = 35
TOLERANCIA_DE_ATRASO_SEGUNDOS = 3600  # se o worker estava parado na hora, ainda roda ao voltar
TOLERANCIA_DE_ATRASO_DE_POSTOS_SEGUNDOS = 24 * 3600  # a coleta de postos demora; vale o dia todo

ID_DIARIO = "alertas-diarios"
ID_DA_PARTIDA = "alertas-na-partida"
ID_MENSAL_DE_POSTOS = "postos-mensais"
ID_DE_POSTOS_NA_PARTIDA = "postos-na-partida"


def deve_coletar_na_partida(
    ultima_tentativa: datetime | None, agora: datetime, limite_horas: int
) -> bool:
    return ultima_tentativa is None or agora - ultima_tentativa > timedelta(hours=limite_horas)


def deve_coletar_postos_na_partida(
    ultima_tentativa: datetime | None, agora: datetime, limite_dias: int = LIMITE_DIAS_DE_POSTOS
) -> bool:
    return ultima_tentativa is None or agora - ultima_tentativa > timedelta(days=limite_dias)


def preparar_agendador(
    rodada: Callable[[], object],
    *,
    ultima_tentativa: datetime | None,
    agora: datetime,
    limite_horas: int,
    rodada_de_postos: Callable[[], object] | None = None,
    ultima_tentativa_de_postos: datetime | None = None,
) -> BlockingScheduler:
    """Agendador pronto para `start()`: alertas todo dia, postos todo mês e, se for o caso, a
    coleta da partida de cada um (alertas primeiro)."""
    agendador = BlockingScheduler(
        timezone=FUSO_DE_BRASILIA, executors={"default": ThreadPoolExecutor(1)}
    )
    agendador.add_job(
        rodada,
        CronTrigger(hour=HORA_DA_COLETA, minute=MINUTO_DA_COLETA, timezone=FUSO_DE_BRASILIA),
        id=ID_DIARIO,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
    )
    if deve_coletar_na_partida(ultima_tentativa, agora, limite_horas):
        agendador.add_job(
            rodada,
            DateTrigger(run_date=agora, timezone=FUSO_DE_BRASILIA),
            id=ID_DA_PARTIDA,
            max_instances=1,
            misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
        )
    if rodada_de_postos is None:
        return agendador

    agendador.add_job(
        rodada_de_postos,
        CronTrigger(
            day=1,
            hour=HORA_DA_COLETA_DE_POSTOS,
            minute=MINUTO_DA_COLETA_DE_POSTOS,
            timezone=FUSO_DE_BRASILIA,
        ),
        id=ID_MENSAL_DE_POSTOS,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=TOLERANCIA_DE_ATRASO_DE_POSTOS_SEGUNDOS,
    )
    if deve_coletar_postos_na_partida(ultima_tentativa_de_postos, agora):
        agendador.add_job(
            rodada_de_postos,
            DateTrigger(run_date=agora, timezone=FUSO_DE_BRASILIA),
            id=ID_DE_POSTOS_NA_PARTIDA,
            max_instances=1,
            misfire_grace_time=TOLERANCIA_DE_ATRASO_DE_POSTOS_SEGUNDOS,
        )
    return agendador
