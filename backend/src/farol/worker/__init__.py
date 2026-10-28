"""Worker: coleta agendada dos alertas e classificação. Topo da arquitetura."""

from farol.worker.agenda import (
    deve_coletar_na_partida,
    deve_coletar_postos_na_partida,
    deve_coletar_vistos_na_partida,
    momento_da_nova_tentativa_de_vistos,
    preparar_agendador,
    retomada_de_vistos,
)
from farol.worker.comando import (
    SituacaoDeVistosNaPartida,
    executar_comando,
    main,
    situacao_de_vistos_na_partida,
)
from farol.worker.jobs import (
    CONTATO_DE_EXEMPLO,
    ClassificadorIndisponivel,
    ContatoInvalido,
    ResultadoDaRodada,
    reclassificar_real,
    rodada_de_alertas,
    rodada_real,
    rodada_real_de_postos,
    rodada_real_de_vistos,
)

__all__ = [
    "CONTATO_DE_EXEMPLO",
    "ClassificadorIndisponivel",
    "ContatoInvalido",
    "ResultadoDaRodada",
    "SituacaoDeVistosNaPartida",
    "deve_coletar_na_partida",
    "deve_coletar_postos_na_partida",
    "deve_coletar_vistos_na_partida",
    "executar_comando",
    "main",
    "momento_da_nova_tentativa_de_vistos",
    "preparar_agendador",
    "reclassificar_real",
    "retomada_de_vistos",
    "rodada_de_alertas",
    "rodada_real",
    "rodada_real_de_postos",
    "rodada_real_de_vistos",
    "situacao_de_vistos_na_partida",
]
