"""Acha territórios citados num texto, com os nomes da busca do site.

Serve ao chat de dois jeitos: o resolvedor da pergunta (`farol.api.chat`) e a indexação, que
grava em cada aviso geral os países que ele cita (`worker`). Sem acento, sem diferença de
maiúscula e por palavra inteira; quando mais de um nome casa no mesmo trecho, vale o mais longo
("Guiné-Bissau" não é "Guiné"). Um nome ambíguo ("Congo") nunca vira um território só.
"""

import re
import unicodedata
from dataclasses import dataclass

from sqlalchemy.orm import Session

from farol.dominio import Territorio, TerritorioRepositorio, TipoTerritorio
from farol.mapa.preparo import nomes_para_titulo

# Nomes que, sozinhos, servem a mais de um território: quem pergunta escolhe, o código nunca
AMBIGUOS: dict[str, tuple[str, ...]] = {
    "congo": ("CG", "CD"),
    "guine": ("GN", "GQ", "GW"),
    "coreia": ("KP", "KR"),
    "ilhas virgens": ("VG", "VI"),
}


def _normalizar(texto: str) -> str:
    """Sem acento, em minúsculas e com um espaço entre as palavras (como o `titulo_cita`)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def _padrao(nome: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(nome)}(?![a-z0-9])")


@dataclass(frozen=True)
class TerritoriosCitados:
    encontrados: tuple[Territorio, ...] = ()  # em ordem de código
    ambiguos: tuple[tuple[Territorio, ...], ...] = ()  # um grupo de candidatos por nome ambíguo


class ProcuradorDeTerritorios:
    """Lê os territórios (menos as áreas neutras) uma vez, ao nascer."""

    def __init__(self, sessao: Session) -> None:
        territorios = [
            t
            for t in TerritorioRepositorio(sessao).listar_todos()
            if t.tipo is not TipoTerritorio.NEUTRO
        ]
        self._territorios = {t.codigo: t for t in territorios}
        self._nomes = {
            t.codigo: sorted(
                # um nome ambíguo nunca resolve sozinho para um território, mesmo se for termo dele
                {_normalizar(n) for n in nomes_para_titulo(t) if n} - AMBIGUOS.keys(),
                key=len,
                reverse=True,
            )
            for t in territorios
        }

    def procurar(self, texto: str) -> TerritoriosCitados:
        restante = _normalizar(texto)
        # nomes mais longos primeiro; o trecho já usado sai do texto para não casar de novo
        casamentos: list[tuple[int, str]] = []
        for codigo, nomes in self._nomes.items():
            for nome in nomes:
                if nome and _padrao(nome).search(restante):
                    casamentos.append((len(nome), codigo))
                    break
        encontrados: list[str] = []
        for _, codigo in sorted(casamentos, key=lambda c: (-c[0], c[1])):
            for nome in self._nomes[codigo]:
                padrao = _padrao(nome)
                if padrao.search(restante):
                    restante = padrao.sub(" ", restante)
                    encontrados.append(codigo)
                    break
        ambiguos = tuple(
            tuple(self._territorios[c] for c in candidatos if c in self._territorios)
            for palavra, candidatos in AMBIGUOS.items()
            if _padrao(palavra).search(restante)
        )
        return TerritoriosCitados(
            encontrados=tuple(self._territorios[c] for c in sorted(encontrados)),
            ambiguos=ambiguos,
        )

    def codigos_citados(self, texto: str) -> frozenset[str]:
        """Todos os códigos que o texto cita, os candidatos de um nome ambíguo incluídos."""
        citados = self.procurar(texto)
        return frozenset(t.codigo for t in citados.encontrados) | {
            t.codigo for grupo in citados.ambiguos for t in grupo
        }
