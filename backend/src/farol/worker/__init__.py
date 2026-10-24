"""Worker: coleta agendada dos alertas e classificação. Topo da arquitetura."""

from farol.worker.agenda import deve_coletar_na_partida, preparar_agendador
from farol.worker.comando import executar_comando, main
from farol.worker.jobs import (
    CONTATO_DE_EXEMPLO,
    ContatoInvalido,
    ResultadoDaRodada,
    rodada_de_alertas,
    rodada_real,
)

__all__ = [
    "CONTATO_DE_EXEMPLO",
    "ContatoInvalido",
    "ResultadoDaRodada",
    "deve_coletar_na_partida",
    "executar_comando",
    "main",
    "preparar_agendador",
    "rodada_de_alertas",
    "rodada_real",
]
