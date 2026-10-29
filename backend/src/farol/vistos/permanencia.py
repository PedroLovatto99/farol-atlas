"""Tempo de permanência (FR-004a): só formatos conhecidos são padronizados.

Nada aqui calcula nem converte números ("3 months" não vira "90 dias") e nada usa o tradutor:
qualquer outro texto fica como a fonte o escreveu, em inglês.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from farol.vistos.normalizacao import normalizar


class TipoDePermanencia(StrEnum):
    """Como o campo de permanência é mostrado (valores gravados em `permanencia_tipo`)."""

    NENHUMA = "nenhuma"  # a fonte não informa
    PADRONIZADA = "padronizada"  # formato conhecido, em português
    ORIGINAL = "original"  # formato desconhecido: como na fonte, em inglês
    PRAZOS_DIVERGENTES = "prazos_divergentes"  # linhas do mesmo território discordam (FR-007)
    VARIA_CONFORME_MOTIVO = "varia_conforme_motivo"  # lista curada por país (FR-007a)


@dataclass(frozen=True)
class Permanencia:
    tipo: TipoDePermanencia
    texto: str | None  # nulo nos tipos que não têm texto (`nenhuma`, divergentes, varia)


_UNIDADES = {
    "day": ("dia", "dias"),
    "week": ("semana", "semanas"),
    "month": ("mês", "meses"),
    "year": ("ano", "anos"),
}
_SIMPLES = re.compile(r"(\d+) (day|week|month|year)s?", flags=re.IGNORECASE)
_PERIODO_DESLIZANTE = re.compile(r"(\d+) days? in any (\d+)[- ]day period", flags=re.IGNORECASE)

SEM_PERMANENCIA = Permanencia(TipoDePermanencia.NENHUMA, None)


def _quantidade(numero: str, singular: str, plural: str) -> str:
    return f"{numero} {singular if int(numero) == 1 else plural}"


def ler_permanencia(texto_da_fonte: str) -> Permanencia:
    """Padroniza o texto da coluna "Allowed stay" se ele tiver um dos formatos conhecidos."""
    texto = normalizar(texto_da_fonte)
    if not texto:
        return SEM_PERMANENCIA

    simples = _SIMPLES.fullmatch(texto)
    if simples:
        singular, plural = _UNIDADES[simples.group(2).lower()]
        return Permanencia(
            TipoDePermanencia.PADRONIZADA, _quantidade(simples.group(1), singular, plural)
        )

    periodo = _PERIODO_DESLIZANTE.fullmatch(texto)
    if periodo:
        dias = _quantidade(periodo.group(1), "dia", "dias")
        janela = _quantidade(periodo.group(2), "dia", "dias")
        return Permanencia(TipoDePermanencia.PADRONIZADA, f"{dias} a cada período de {janela}")

    return Permanencia(TipoDePermanencia.ORIGINAL, texto)
