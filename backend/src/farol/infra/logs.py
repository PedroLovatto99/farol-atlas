"""Log estruturado: uma linha JSON por evento, fácil de ler por pessoas e por ferramentas."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class FormatadorJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        evento: dict[str, Any] = {
            "instante": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        extras = getattr(record, "dados", None)
        if isinstance(extras, dict):
            evento.update(extras)
        if record.exc_info:
            evento["excecao"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False, default=str)


def configurar_logs(nivel: str = "INFO") -> None:
    """Configura o log da aplicação para sair em JSON na saída padrão."""
    manipulador = logging.StreamHandler(sys.stdout)
    manipulador.setFormatter(FormatadorJson())
    raiz = logging.getLogger()
    raiz.handlers = [manipulador]
    raiz.setLevel(nivel)


def obter_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
