"""Relógio injetável: permite testar regras que dependem da hora (ex.: dados com mais de 3 dias)."""

from datetime import UTC, datetime
from typing import Protocol


class Relogio(Protocol):
    def agora(self) -> datetime:
        """Instante atual, sempre com fuso (UTC)."""
        ...


class RelogioDoSistema:
    def agora(self) -> datetime:
        return datetime.now(UTC)
