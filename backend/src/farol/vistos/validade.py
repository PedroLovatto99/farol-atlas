"""Validade da coleta (FR-010): só uma coleta válida pode mudar o que o site mostra.

Válida = artigo no formato esperado e países reconhecidos pelo menos no mínimo: 90% dos reconhecidos
na última coleta válida, ou um piso fixo de 150 na primeira. "Reconhecidos" são os códigos distintos
do mapa ligados a alguma linha, sem contar os nomes ignorados de propósito.
"""

from dataclasses import dataclass

MINIMO_NA_PRIMEIRA_COLETA = 150
FRACAO_MINIMA = (9, 10)  # 90%, em conta de inteiros (sem ponto flutuante)
MANUTENCAO_DO_LEITOR = "; o leitor da página precisa de manutenção (mudança de estrutura na fonte)"


@dataclass(frozen=True)
class VeredictoDaValidade:
    valida: bool
    reconhecidos: int
    minimo: int
    motivo: str | None  # nulo quando válida


def minimo_de_reconhecidos(reconhecidos_anteriores: int | None) -> int:
    """O mínimo desta coleta; o 90% arredonda para cima (90% de 226 é 203,4: o mínimo é 204)."""
    if reconhecidos_anteriores is None:
        return MINIMO_NA_PRIMEIRA_COLETA
    numerador, denominador = FRACAO_MINIMA
    return -(-reconhecidos_anteriores * numerador // denominador)


def avaliar_validade(
    reconhecidos: int,
    *,
    formato_esperado: bool,
    reconhecidos_anteriores: int | None,
    detalhe_do_formato: str | None = None,
) -> VeredictoDaValidade:
    """Aplica os dois critérios do FR-010. `reconhecidos_anteriores` é nulo na primeira coleta."""
    minimo = minimo_de_reconhecidos(reconhecidos_anteriores)
    if not formato_esperado:
        motivo = "formato inesperado"
        if detalhe_do_formato:
            motivo = f"{motivo}: {detalhe_do_formato}"
        motivo += MANUTENCAO_DO_LEITOR
        return VeredictoDaValidade(False, reconhecidos, minimo, motivo)
    if reconhecidos < minimo:
        base = (
            "piso da primeira coleta"
            if reconhecidos_anteriores is None
            else f"90% dos {reconhecidos_anteriores} da última coleta válida"
        )
        motivo = f"só {reconhecidos} países reconhecidos (mínimo {minimo}: {base})"
        return VeredictoDaValidade(False, reconhecidos, minimo, motivo)
    return VeredictoDaValidade(True, reconhecidos, minimo, None)
