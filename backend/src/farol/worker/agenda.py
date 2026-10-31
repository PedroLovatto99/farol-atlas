"""Agendamento do worker (D5): coleta diária às 06:17 de Brasília e coleta na partida.

Na partida, o worker coleta logo se a última TENTATIVA tiver mais de `limite_horas` (padrão 20 h),
para um servidor reiniciado não esperar até o dia seguinte. Uma falha recente não é repetida antes
do dia seguinte: a spec tolera até 3 dias sem coleta completa.

A coleta de postos (endereço e telefone) é mensal: dia 1, às 05:43. Na partida, só roda se a última
tentativa tiver mais de 35 dias, para uma instalação nova não ficar um mês sem contatos.

A coleta de vistos (Wikipédia) é semanal: segunda-feira, às 05:13 (decisão O5 da 002: o job mensal
de postos, às 05:43, demora cerca de 45 minutos, e o worker tem um fio só). Na partida, só roda se
não há coleta VÁLIDA ou se a última tem mais de 7 dias; senão, não faz requisição nenhuma. Se a
última tentativa foi BLOQUEADA, não insiste na partida: a próxima é a da agenda semanal. Uma
rodada `adiada` (artigo editado há menos de 24 h) ou que `falhou` ganha uma nova tentativa às 05:13
do dia seguinte (`vistos-amanha`), até 3 falhas seguidas (O6); depois disso, só a próxima segunda.
Ao subir, o worker retoma uma tentativa de amanhã que a parada dele deixou pendente.

Os jobs rodam um de cada vez (um só fio de execução): o gov.br e a Wikipédia recebem uma requisição
por vez, com a pausa do cliente educado, mesmo quando duas coletas caem juntas.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from farol.dominio import ResultadoDaColetaDeVistos
from farol.infra import FUSO_DE_BRASILIA, Relogio, RelogioDoSistema
from farol.vistos import ProximaTentativa, proxima_tentativa

HORA_DA_COLETA = 6
MINUTO_DA_COLETA = 17
HORA_DA_COLETA_DE_POSTOS = 5
MINUTO_DA_COLETA_DE_POSTOS = 43
LIMITE_DIAS_DE_POSTOS = 35
HORA_DA_COLETA_DE_VISTOS = 5
MINUTO_DA_COLETA_DE_VISTOS = 13
LIMITE_DIAS_DE_VISTOS = 7
TOLERANCIA_DE_ATRASO_SEGUNDOS = 3600  # se o worker estava parado na hora, ainda roda ao voltar
TOLERANCIA_DE_ATRASO_DE_POSTOS_SEGUNDOS = 24 * 3600  # a coleta de postos demora; vale o dia todo

ID_DIARIO = "alertas-diarios"
ID_DA_PARTIDA = "alertas-na-partida"
ID_MENSAL_DE_POSTOS = "postos-mensais"
ID_DE_POSTOS_NA_PARTIDA = "postos-na-partida"
ID_SEMANAL_DE_VISTOS = "vistos-semanais"
ID_DE_VISTOS_NA_PARTIDA = "vistos-na-partida"
ID_DE_VISTOS_AMANHA = "vistos-amanha"


def deve_coletar_na_partida(
    ultima_tentativa: datetime | None, agora: datetime, limite_horas: int
) -> bool:
    return ultima_tentativa is None or agora - ultima_tentativa > timedelta(hours=limite_horas)


def deve_coletar_postos_na_partida(
    ultima_tentativa: datetime | None, agora: datetime, limite_dias: int = LIMITE_DIAS_DE_POSTOS
) -> bool:
    return ultima_tentativa is None or agora - ultima_tentativa > timedelta(days=limite_dias)


def deve_coletar_vistos_na_partida(
    ultima_coleta_valida: datetime | None,
    agora: datetime,
    limite_dias: int = LIMITE_DIAS_DE_VISTOS,
    *,
    ultima_tentativa_bloqueada: bool = False,
) -> bool:
    """Só sem coleta válida ou com a última válida de mais de 7 dias. Uma tentativa que falhou,
    foi adiada ou rejeitada não conta: o que vale é o dado que o site mostra.

    Exceção: se a última tentativa foi **bloqueada** (403, 429, verificação humana ou `robots.txt`),
    não insiste ao reiniciar: a próxima tentativa é a da agenda semanal. A rejeitada por formato
    pode tentar na partida, porque o reinício costuma vir do deploy da correção.
    """
    if ultima_tentativa_bloqueada:
        return False
    return ultima_coleta_valida is None or agora - ultima_coleta_valida > timedelta(
        days=limite_dias
    )


def momento_da_nova_tentativa_de_vistos(
    proxima: ProximaTentativa, depois_de: datetime
) -> datetime | None:
    """O horário da nova tentativa: 05:13 do dia seguinte (em Brasília) a `depois_de`.

    Nulo quando a próxima tentativa é a segunda-feira: quem a faz é o job semanal.
    """
    if proxima is not ProximaTentativa.AMANHA:
        return None
    amanha = depois_de.astimezone(FUSO_DE_BRASILIA) + timedelta(days=1)
    return amanha.replace(
        hour=HORA_DA_COLETA_DE_VISTOS,
        minute=MINUTO_DA_COLETA_DE_VISTOS,
        second=0,
        microsecond=0,
    )


def retomada_de_vistos(
    resultado: ResultadoDaColetaDeVistos | None,
    adiamentos_seguidos: int,
    falhas_seguidas: int,
    iniciada_em: datetime | None,
) -> datetime | None:
    """Ao subir o worker: quando a última tentativa pede uma nova "amanhã", o horário dela.

    As contagens são as da própria última tentativa (inclusive ela). Nulo se não há o que retomar.
    """
    if resultado is None or iniciada_em is None:
        return None
    proxima = proxima_tentativa(
        resultado, adiamentos_seguidos=adiamentos_seguidos, falhas_seguidas=falhas_seguidas
    )
    return momento_da_nova_tentativa_de_vistos(proxima, iniciada_em)


def agendador_ocioso() -> BlockingScheduler:
    """Agendador sem nenhum job: o worker fica de pé sem coletar nada (COLETAS_AUTOMATICAS=false).

    Os comandos de coleta única (`coletar --alertas` etc.) seguem funcionando.
    """
    return BlockingScheduler(
        timezone=FUSO_DE_BRASILIA, executors={"default": ThreadPoolExecutor(1)}
    )


def preparar_agendador(
    rodada: Callable[[], object],
    *,
    ultima_tentativa: datetime | None,
    agora: datetime,
    limite_horas: int,
    rodada_de_postos: Callable[[], object] | None = None,
    ultima_tentativa_de_postos: datetime | None = None,
    rodada_de_vistos: Callable[[], ProximaTentativa] | None = None,
    ultima_coleta_valida_de_vistos: datetime | None = None,
    ultima_tentativa_de_vistos_bloqueada: bool = False,
    retomada_de_vistos: datetime | None = None,
    relogio: Relogio | None = None,
) -> BlockingScheduler:
    """Agendador pronto para `start()`: alertas todo dia, postos todo mês, vistos toda semana e,
    se for o caso, a coleta da partida de cada um (alertas primeiro).

    `rodada_de_vistos` devolve quando tentar de novo; `retomada_de_vistos` é a tentativa de
    "amanhã" que a parada do worker deixou pendente (veja `retomada_de_vistos` acima).
    """
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
    if rodada_de_postos is not None:
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
    if rodada_de_vistos is not None:
        _agendar_vistos(
            agendador,
            rodada_de_vistos,
            ultima_coleta_valida=ultima_coleta_valida_de_vistos,
            bloqueada=ultima_tentativa_de_vistos_bloqueada,
            agora=agora,
            retomada=retomada_de_vistos,
            relogio=relogio or RelogioDoSistema(),
        )
    return agendador


def _agendar_vistos(
    agendador: BlockingScheduler,
    rodada_de_vistos: Callable[[], ProximaTentativa],
    *,
    ultima_coleta_valida: datetime | None,
    bloqueada: bool,
    agora: datetime,
    retomada: datetime | None,
    relogio: Relogio,
) -> None:
    def rodada() -> None:
        """Roda a coleta e, se ela pede, marca a nova tentativa de amanhã às 05:13."""
        proxima = rodada_de_vistos()
        quando = momento_da_nova_tentativa_de_vistos(proxima, relogio.agora())
        if quando is not None:
            agendador.add_job(
                rodada,
                DateTrigger(run_date=quando, timezone=FUSO_DE_BRASILIA),
                id=ID_DE_VISTOS_AMANHA,
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
            )

    agendador.add_job(
        rodada,
        CronTrigger(
            day_of_week="mon",
            hour=HORA_DA_COLETA_DE_VISTOS,
            minute=MINUTO_DA_COLETA_DE_VISTOS,
            timezone=FUSO_DE_BRASILIA,
        ),
        id=ID_SEMANAL_DE_VISTOS,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
    )
    if retomada is not None:
        # a tentativa de amanhã que ficou pendente cobre também a coleta atrasada da partida;
        # se o horário já passou com o worker parado, roda agora
        agendador.add_job(
            rodada,
            DateTrigger(run_date=max(retomada, agora), timezone=FUSO_DE_BRASILIA),
            id=ID_DE_VISTOS_AMANHA,
            max_instances=1,
            misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
        )
    elif deve_coletar_vistos_na_partida(
        ultima_coleta_valida, agora, ultima_tentativa_bloqueada=bloqueada
    ):
        agendador.add_job(
            rodada,
            DateTrigger(run_date=agora, timezone=FUSO_DE_BRASILIA),
            id=ID_DE_VISTOS_NA_PARTIDA,
            max_instances=1,
            misfire_grace_time=TOLERANCIA_DE_ATRASO_SEGUNDOS,
        )
