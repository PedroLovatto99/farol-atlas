"""Exporta o OpenAPI do app em JSON, para gerar os tipos do frontend (openapi-typescript).

Uso: uv run poe exportar-openapi [caminho]   (sem caminho, escreve na saída padrão)
Não precisa de banco nem de variáveis de ambiente.
"""

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from farol.api.app import criar_app
from farol.infra import Configuracoes


def gerar_openapi() -> dict[str, Any]:
    configuracoes = Configuracoes(
        database_url=SecretStr("postgresql+psycopg://sem-banco/sem-banco"),
        api_docs_habilitada=False,
    )
    return criar_app(configuracoes).openapi()


def main(argumentos: list[str]) -> int:
    texto = json.dumps(gerar_openapi(), ensure_ascii=False, indent=2) + "\n"
    if argumentos:
        Path(argumentos[0]).write_text(texto, encoding="utf-8")
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
