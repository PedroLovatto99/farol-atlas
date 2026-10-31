"""Log estruturado: uma linha JSON por evento, fácil de ler por pessoas e por ferramentas."""

import json
import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

NOME_DO_ARQUIVO = "worker.log"
TAMANHO_MAXIMO_DO_ARQUIVO = 5 * 1024 * 1024
COPIAS_DO_ARQUIVO = 5


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


def configurar_logs(nivel: str = "INFO", *, diretorio: Path | None = None) -> None:
    """Configura o log da aplicação para sair em JSON na saída padrão.

    Com `diretorio`, grava também em `worker.log` lá dentro (rotativo, 5 MB x 5 cópias). Numa pasta
    de volume do Docker, o arquivo sobrevive à recriação do contêiner.
    """
    formatador = FormatadorJson()
    manipuladores: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if diretorio is not None:
        diretorio.mkdir(parents=True, exist_ok=True)
        manipuladores.append(
            logging.handlers.RotatingFileHandler(
                diretorio / NOME_DO_ARQUIVO,
                maxBytes=TAMANHO_MAXIMO_DO_ARQUIVO,
                backupCount=COPIAS_DO_ARQUIVO,
                encoding="utf-8",
            )
        )
    raiz = logging.getLogger()
    for antigo in raiz.handlers:
        antigo.close()
    for manipulador in manipuladores:
        manipulador.setFormatter(formatador)
    raiz.handlers = manipuladores
    raiz.setLevel(nivel)


def obter_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
