"""Estabilidade da fonte e calendário das novas tentativas (D3; decisões O5 e O6)."""

from datetime import UTC, datetime, timedelta

import pytest

from farol.dominio import ResultadoDaColetaDeVistos as Resultado
from farol.vistos.estabilidade import (
    LIMITE_DE_ADIAMENTOS,
    LIMITE_DE_FALHAS,
    ProximaTentativa,
    avaliar_estabilidade,
    proxima_tentativa,
)

AGORA = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------- edição recente
def test_edicao_de_menos_de_24_horas_adia() -> None:
    decisao = avaliar_estabilidade(AGORA - timedelta(hours=6), AGORA, adiamentos_seguidos=0)
    assert decisao.adiar is True
    assert decisao.idade == timedelta(hours=6)


def test_edicao_de_24_horas_ou_mais_coleta() -> None:
    assert not avaliar_estabilidade(AGORA - timedelta(hours=24), AGORA, 0).adiar
    assert not avaliar_estabilidade(AGORA - timedelta(days=9), AGORA, 0).adiar


def test_um_minuto_antes_das_24_horas_ainda_adia() -> None:
    assert avaliar_estabilidade(AGORA - timedelta(hours=23, minutes=59), AGORA, 0).adiar


def test_edicao_no_futuro_por_diferenca_de_relogio_adia() -> None:
    assert avaliar_estabilidade(AGORA + timedelta(minutes=5), AGORA, 0).adiar


def test_depois_de_3_adiamentos_seguidos_coleta_mesmo_assim() -> None:
    recente = AGORA - timedelta(hours=1)
    assert LIMITE_DE_ADIAMENTOS == 3
    assert avaliar_estabilidade(recente, AGORA, adiamentos_seguidos=2).adiar
    decisao = avaliar_estabilidade(recente, AGORA, adiamentos_seguidos=3)
    assert decisao.adiar is False
    assert decisao.forcada is True


def test_edicao_antiga_nao_e_forcada() -> None:
    assert avaliar_estabilidade(AGORA - timedelta(days=3), AGORA, 3).forcada is False


# --------------------------------------------------------------------------- próxima tentativa
def test_adiada_tenta_de_novo_amanha() -> None:
    for seguidas in range(4):
        assert (
            proxima_tentativa(Resultado.ADIADA, adiamentos_seguidos=seguidas, falhas_seguidas=0)
            is ProximaTentativa.AMANHA
        )


def test_falha_tecnica_tenta_amanha_ate_3_seguidas() -> None:
    assert LIMITE_DE_FALHAS == 3
    for falhas in (1, 2):
        assert (
            proxima_tentativa(Resultado.FALHOU, adiamentos_seguidos=0, falhas_seguidas=falhas)
            is ProximaTentativa.AMANHA
        )


def test_na_terceira_falha_seguida_so_na_proxima_segunda() -> None:
    assert (
        proxima_tentativa(Resultado.FALHOU, adiamentos_seguidos=0, falhas_seguidas=3)
        is ProximaTentativa.PROXIMA_SEGUNDA
    )
    assert (
        proxima_tentativa(Resultado.FALHOU, adiamentos_seguidos=0, falhas_seguidas=4)
        is ProximaTentativa.PROXIMA_SEGUNDA
    )


@pytest.mark.parametrize("resultado", [Resultado.BLOQUEADA, Resultado.REJEITADA, Resultado.VALIDA])
def test_bloqueio_rejeicao_e_coleta_valida_esperam_a_proxima_segunda(
    resultado: Resultado,
) -> None:
    # bloqueio (403, 429, verificação humana, robots.txt) nunca insiste
    assert (
        proxima_tentativa(resultado, adiamentos_seguidos=0, falhas_seguidas=0)
        is ProximaTentativa.PROXIMA_SEGUNDA
    )
