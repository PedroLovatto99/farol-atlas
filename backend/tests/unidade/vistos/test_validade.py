"""Validade da coleta de vistos (FR-010): formato esperado e países reconhecidos suficientes."""

import pytest

from farol.vistos.consolidacao import consolidar
from farol.vistos.dicionario import Dicionario
from farol.vistos.fonte import LinhaDaFonte
from farol.vistos.validade import (
    MINIMO_NA_PRIMEIRA_COLETA,
    avaliar_validade,
    minimo_de_reconhecidos,
)


# --------------------------------------------------------------------------- o mínimo
def test_primeira_coleta_exige_150_reconhecidos() -> None:
    assert MINIMO_NA_PRIMEIRA_COLETA == 150
    assert minimo_de_reconhecidos(None) == 150


@pytest.mark.parametrize(
    ("anterior", "minimo"),
    [
        (226, 204),  # 90% de 226 = 203,4: arredonda para cima
        (200, 180),  # exato, sem sobra
        (10, 9),
        (1, 1),
    ],
)
def test_depois_da_primeira_o_minimo_e_90_por_cento_da_ultima_coleta_valida(
    anterior: int, minimo: int
) -> None:
    assert minimo_de_reconhecidos(anterior) == minimo


def test_o_piso_de_150_nao_vale_depois_da_primeira_coleta() -> None:
    # com uma coleta anterior pequena, vale só a regra dos 90%
    assert minimo_de_reconhecidos(100) == 90


# --------------------------------------------------------------------------- o veredito
def test_203_de_226_rejeita_e_204_aceita() -> None:
    rejeitada = avaliar_validade(203, formato_esperado=True, reconhecidos_anteriores=226)
    aceita = avaliar_validade(204, formato_esperado=True, reconhecidos_anteriores=226)
    assert rejeitada.valida is False
    assert aceita.valida is True
    assert rejeitada.minimo == aceita.minimo == 204


def test_o_motivo_da_rejeicao_diz_quantos_foram_reconhecidos_e_o_minimo() -> None:
    veredito = avaliar_validade(203, formato_esperado=True, reconhecidos_anteriores=226)
    assert veredito.motivo is not None
    assert "203" in veredito.motivo
    assert "204" in veredito.motivo
    assert "226" in veredito.motivo  # a base dos 90%


def test_coleta_valida_nao_tem_motivo() -> None:
    assert avaliar_validade(226, formato_esperado=True, reconhecidos_anteriores=226).motivo is None


def test_primeira_coleta_149_rejeita_e_150_aceita() -> None:
    assert not avaliar_validade(149, formato_esperado=True, reconhecidos_anteriores=None).valida
    assert avaliar_validade(150, formato_esperado=True, reconhecidos_anteriores=None).valida


def test_mais_reconhecidos_que_antes_e_valido() -> None:
    assert avaliar_validade(240, formato_esperado=True, reconhecidos_anteriores=226).valida


def test_formato_inesperado_rejeita_mesmo_com_todos_os_paises() -> None:
    veredito = avaliar_validade(
        226,
        formato_esperado=False,
        reconhecidos_anteriores=226,
        detalhe_do_formato="faltam tabelas esperadas",
    )
    assert veredito.valida is False
    assert veredito.motivo is not None
    assert "formato inesperado" in veredito.motivo
    assert "leitor da página precisa de manutenção" in veredito.motivo
    assert "faltam tabelas esperadas" in veredito.motivo


def test_formato_inesperado_vale_tambem_na_primeira_coleta() -> None:
    assert not avaliar_validade(0, formato_esperado=False, reconhecidos_anteriores=None).valida


# --------------------------------------------------------------------------- o que conta
def test_os_ignorados_nao_contam_como_reconhecidos(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    consolidacao = consolidar(linhas_da_fonte, dicionario_real)
    assert len(consolidacao.ignoradas) == 19
    # 249 linhas lidas, 19 ignoradas e 3 linhas de Santa Helena no mesmo código: 228 códigos
    assert len(linhas_da_fonte) == 249
    assert consolidacao.paises_reconhecidos == 228
    assert avaliar_validade(
        consolidacao.paises_reconhecidos, formato_esperado=True, reconhecidos_anteriores=228
    ).valida


def test_a_fixture_inteira_passa_na_primeira_coleta(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    reconhecidos = consolidar(linhas_da_fonte, dicionario_real).paises_reconhecidos
    assert avaliar_validade(
        reconhecidos, formato_esperado=True, reconhecidos_anteriores=None
    ).valida
