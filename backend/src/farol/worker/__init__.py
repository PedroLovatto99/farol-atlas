"""Worker: coleta agendada dos alertas e classificação. Topo da arquitetura."""

from farol.worker.agenda import (
    deve_coletar_na_partida,
    deve_coletar_postos_na_partida,
    preparar_agendador,
)
from farol.worker.comando import executar_comando, main
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
    "deve_coletar_na_partida",
    "deve_coletar_postos_na_partida",
    "executar_comando",
    "main",
    "preparar_agendador",
    "reclassificar_real",
    "rodada_de_alertas",
    "rodada_real",
    "rodada_real_de_postos",
    "rodada_real_de_vistos",
]
