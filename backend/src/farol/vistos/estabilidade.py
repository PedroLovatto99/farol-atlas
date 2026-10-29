"""Estabilidade da fonte e calendário das novas tentativas (decisões D3, O5 e O6).

Funções puras: o serviço de coleta lê o histórico do banco e passa os números; quem agenda
(`worker/agenda.py`) traduz `ProximaTentativa` em um horário.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from farol.dominio import ResultadoDaColetaDeVistos

IDADE_MINIMA_DA_EDICAO = timedelta(hours=24)
LIMITE_DE_ADIAMENTOS = 3  # depois de 3 `adiada` seguidas, coleta mesmo assim
LIMITE_DE_FALHAS = 3  # depois de 3 `falhou` seguidas, só na próxima segunda


class ProximaTentativa(StrEnum):
    AMANHA = "amanha"  # 05:13 do dia seguinte
    PROXIMA_SEGUNDA = "proxima_segunda"  # o job semanal


@dataclass(frozen=True)
class DecisaoDeEstabilidade:
    adiar: bool
    idade: timedelta  # há quanto tempo o artigo foi editado
    forcada: bool  # edição recente, mas o limite de adiamentos acabou: coleta mesmo assim


def avaliar_estabilidade(
    ultima_edicao: datetime, agora: datetime, adiamentos_seguidos: int
) -> DecisaoDeEstabilidade:
    """Adia se o artigo foi editado há menos de 24 h, a menos que já tenham sido 3 adiamentos.

    `adiamentos_seguidos` são as tentativas `adiada` que vieram logo antes desta.
    """
    idade = agora - ultima_edicao
    recente = idade < IDADE_MINIMA_DA_EDICAO
    esgotou = adiamentos_seguidos >= LIMITE_DE_ADIAMENTOS
    return DecisaoDeEstabilidade(
        adiar=recente and not esgotou, idade=idade, forcada=recente and esgotou
    )


def proxima_tentativa(
    resultado: ResultadoDaColetaDeVistos, *, adiamentos_seguidos: int, falhas_seguidas: int
) -> ProximaTentativa:
    """Quando tentar de novo depois de uma tentativa (contagens incluem a própria tentativa).

    - `adiada`: amanhã (a quarta tentativa coleta, mesmo com a edição recente);
    - `falhou`: amanhã, até 3 falhas seguidas; depois, só a próxima segunda (O6);
    - `bloqueada` (403, 429, verificação humana, `robots.txt`), `rejeitada` e `valida`: a próxima
      segunda. Bloqueio nunca insiste.
    """
    if resultado is ResultadoDaColetaDeVistos.ADIADA:
        return ProximaTentativa.AMANHA
    if resultado is ResultadoDaColetaDeVistos.FALHOU and falhas_seguidas < LIMITE_DE_FALHAS:
        return ProximaTentativa.AMANHA
    return ProximaTentativa.PROXIMA_SEGUNDA
