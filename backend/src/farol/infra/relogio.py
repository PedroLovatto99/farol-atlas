"""Relógio injetável: permite testar regras que dependem da hora (ex.: dados com mais de 3 dias)."""

from datetime import UTC, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

# O Portal Consular, o agendamento e as datas do site usam o horário de Brasília
FUSO_DE_BRASILIA = ZoneInfo("America/Sao_Paulo")


class Relogio(Protocol):
    def agora(self) -> datetime:
        """Instante atual, sempre com fuso (UTC)."""
        ...


class RelogioDoSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)
