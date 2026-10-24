"""Agendamento do worker (D5): coleta diária às 06:17 de Brasília e coleta na partida.

Na partida, o worker coleta logo se a última TENTATIVA tiver mais de `limite_horas` (padrão 20 h),
para um servidor reiniciado não esperar até o dia seguinte. Uma falha recente não é repetida antes
do dia seguinte: a spec tolera até 3 dias sem coleta completa.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

FUSO = ZoneInfo("America/Sao_Paulo")
HORA_DA_COLETA = 6
MINUTO_DA_COLETA = 17
TOLERANCIA_DE_ATRASO_SEGUNDOS = 3600  # se o worker estava parado na hora, ainda roda ao voltar

ID_DIARIO = "alertas-diarios"
ID_DA_PARTIDA = "alertas-na-partida"


def deve_coletar_na_partida(
    ultima_tentativa: datetime | None, agora: datetime, limite_horas: int
) -> bool:
    return ultima_tentativa is None or agora - ultima_tentativa > timedelta(hours=limite_horas)


def preparar_agendador(
    rodada: Callable[[], object],
    *,
    ultima_tentativa: datetime | None,
    agora: datetime,
    limite_horas: int,
) -> BlockingScheduler:
    """Agendador pronto para `start()`, com o cron diário e, se for o caso, a coleta da partida."""
    agendador = BlockingScheduler(timezone=FUSO)
    agendador.add_job(
        rodada,
        CronTrigger(hour=HORA_DA_COLETA, minute=MINUTO_DA_COLETA, timezone=FUSO),
        id=ID_DIARIO,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
    )
    if deve_coletar_na_partida(ultima_tentativa, agora, limite_horas):
        agendador.add_job(
            rodada,
            DateTrigger(run_date=agora, timezone=FUSO),
            id=ID_DA_PARTIDA,
            max_instances=1,
            misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
        )
    return agendador
