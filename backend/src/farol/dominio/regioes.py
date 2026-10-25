"""Expressões que o Itamaraty usa para dizer "o país inteiro" e que não são uma região.

"Não viajar: Sul do Líbano. Evitar viagens não essenciais: Líbano (demais regiões do país)": o
Sul é uma região; "demais regiões do país" é o nível do país. Quem guardasse a expressão como
região deixaria o país "sem alerta" e o painel diria que o alerta vale só para a região.
"""

import re
import unicodedata
from collections.abc import Sequence

from farol.dominio.enums import NivelAlerta

_GRAVIDADE = {NivelAlerta.NORMALIZADA: 1, NivelAlerta.EVITAR: 2, NivelAlerta.NAO_VIAJAR: 3}

_ALVO = r"(?:pais|territorio)"
_EXPRESSOES_DO_PAIS_INTEIRO = re.compile(
    rf"""
      (?:(?:as|os|o|a)\ )?(?:demais|restante|resto)\ (?:d[oae]s?\ )?
          (?:regioes|areas|localidades|partes|{_ALVO})(?:\ d[oae]\ {_ALVO})?
    | (?:em\ )?todo\ (?:o\ )?{_ALVO}
    | (?:o\ )?{_ALVO}\ (?:inteiro|todo)
    """,
    re.VERBOSE,
)


def _limpar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    so_palavras = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())
    return " ".join(so_palavras.split())


def e_nivel_do_pais(nome: str) -> bool:
    """O "nome de região" é o país inteiro ("demais regiões do país", "todo o país")."""
    return _EXPRESSOES_DO_PAIS_INTEIRO.fullmatch(_limpar(nome)) is not None


def separar_nivel_do_pais(
    nivel_pais: NivelAlerta | None, regioes: Sequence[tuple[str, NivelAlerta]]
) -> tuple[NivelAlerta | None, list[tuple[str, NivelAlerta]]]:
    """Tira das regiões as que são o país inteiro e as soma ao nível do país.

    Se o país já tinha nível e a expressão traz outro, vale o mais grave (na dúvida, nunca esconde
    um "não viaje"). As regiões nomeadas seguem na ordem em que vieram.
    """
    nomeadas: list[tuple[str, NivelAlerta]] = []
    niveis = [] if nivel_pais is None else [nivel_pais]
    for nome, nivel in regioes:
        if e_nivel_do_pais(nome):
            niveis.append(nivel)
        else:
            nomeadas.append((nome, nivel))
    return max(niveis, key=_GRAVIDADE.__getitem__, default=None), nomeadas
