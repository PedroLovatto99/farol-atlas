"""DTOs (Pydantic) de entrada e saída da API. Nenhuma rota devolve objetos do banco."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Erro(BaseModel):
    detalhe: str


class Saude(BaseModel):
    banco: Literal["ok", "falha"]
    ultima_coleta_completa_em: datetime | None
    ultima_tentativa_em: datetime | None
    alertas_pendentes: int
