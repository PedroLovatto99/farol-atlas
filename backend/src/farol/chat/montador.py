"""Monta a resposta que vai à pessoa. Tudo o que é dado vem do código, nunca do modelo.

As citações (título, data, link, "em vigor"/"anterior" e o trecho do "Ver trecho") saem dos
artefatos das ferramentas: o trecho é `alerta.texto[inicio:fim]`, igual ao original. Do modelo só
fica a prosa, e só quando o verificador a aceitou. Uma resposta que afirma algo sem nenhum trecho
para mostrar vira "não encontrei": o chat não inventa.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from farol.chat.ferramentas import TrechoUsado

Situacao = Literal["resposta", "nao_encontrei", "recusa", "pergunta_de_volta", "so_registros"]

NAO_ENCONTREI = (
    "Não encontrei isso nos alertas nem nos dados do site. Confira o painel do país no mapa ou o "
    "Portal Consular do Itamaraty."
)
SEM_DADOS = (
    "Ainda não há dados coletados do Portal Consular, então não tenho como responder. Tente de "
    "novo mais tarde."
)
TEXTO_DA_CONTINGENCIA = (
    "Não consegui montar uma resposta verificada. Veja abaixo os trechos dos alertas que "
    "encontrei, com o texto original."
)
AVISO_DE_ALERTA_ANTERIOR = (
    "Algum trecho citado é de um alerta anterior: o que vale hoje é o alerta em vigor do país."
)


@dataclass(frozen=True)
class Citacao:
    tipo: Literal["alerta", "nivel", "visto", "postos"]
    titulo: str
    data: datetime | None
    url: str | None
    vigor: Literal["em_vigor", "anterior", "nao_se_aplica"]
    trecho: str | None
    licenca: str | None = None


@dataclass(frozen=True)
class RespostaMontada:
    situacao: Situacao
    texto: str
    citacoes: tuple[Citacao, ...] = ()
    avisos: tuple[str, ...] = ()
    cartoes: tuple[object, ...] = ()  # os cartões de nível, visto e postos chegam com a US2


def _citacoes(trechos: Sequence[TrechoUsado]) -> tuple[Citacao, ...]:
    vistos: set[tuple[int, int, int]] = set()
    citacoes: list[Citacao] = []
    for t in trechos:
        chave = (t.alerta_id, t.inicio, t.fim)
        if chave in vistos:
            continue
        vistos.add(chave)
        citacoes.append(
            Citacao(
                tipo="alerta",
                titulo=t.titulo,
                data=t.data,
                url=t.url,
                vigor=t.vigor,
                trecho=t.trecho,
            )
        )
    return tuple(citacoes)


def _avisos(citacoes: Sequence[Citacao]) -> tuple[str, ...]:
    return (AVISO_DE_ALERTA_ANTERIOR,) if any(c.vigor == "anterior" for c in citacoes) else ()


def montar_resposta(
    situacao: Literal["resposta", "nao_encontrei", "recusa"],
    texto: str,
    trechos: Sequence[TrechoUsado],
) -> RespostaMontada:
    """A resposta a partir do que o modelo declarou e dos trechos que as ferramentas entregaram."""
    if situacao == "recusa":
        return RespostaMontada("recusa", texto)
    citacoes = _citacoes(trechos)
    if situacao == "nao_encontrei" or not citacoes:
        return RespostaMontada("nao_encontrei", NAO_ENCONTREI)
    return RespostaMontada("resposta", texto, citacoes, _avisos(citacoes))


def montar_pergunta_de_volta(texto: str) -> RespostaMontada:
    return RespostaMontada("pergunta_de_volta", texto)


def montar_sem_dados() -> RespostaMontada:
    return RespostaMontada("nao_encontrei", SEM_DADOS)


def montar_contingencia(trechos: Sequence[TrechoUsado]) -> RespostaMontada:
    """Sem prosa confiável: só os trechos, com uma frase fixa do sistema."""
    citacoes = _citacoes(trechos)
    if not citacoes:
        return RespostaMontada("nao_encontrei", NAO_ENCONTREI)
    return RespostaMontada("so_registros", TEXTO_DA_CONTINGENCIA, citacoes, _avisos(citacoes))
