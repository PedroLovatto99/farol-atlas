"""Texto comparável: sem acentos e em minúsculas. Uso interno do módulo `coleta`."""

import re
import unicodedata


def sem_acentos(texto: str) -> str:
    """ "Pretória" vira "pretoria"."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def chave_de_comparacao(texto: str) -> str:
    """Sem acentos, em minúsculas e só com letras e números: compara "Cidade do México" com
    "cidade-do-mexico"."""
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos(texto)).strip()
