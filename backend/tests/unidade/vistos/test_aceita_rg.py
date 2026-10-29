"""Regra do RG (O2): só `Freedom of Movement` com a frase "ID card" na nota."""

import logging

import pytest

from farol.dominio import CategoriaDeVisto
from farol.vistos.dicionario import Dicionario
from farol.vistos.fonte import LinhaDaFonte

COM_RG = {"AR", "BO", "CL", "CO", "EC", "PY", "PE", "UY"}


def _com_rg(dicionario: Dicionario, linhas: list[LinhaDaFonte]) -> set[str]:
    codigos = set()
    for linha in linhas:
        if dicionario.classificar_rotulo(linha.rotulo, linha.notas).aceita_rg:
            codigo = dicionario.ligar_nome(linha.nome).codigo
            assert codigo is not None
            codigos.add(codigo)
    return codigos


def test_oito_de_oito_na_fixture(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    assert _com_rg(dicionario_real, linhas_da_fonte) == COM_RG


def test_guiana_e_venezuela_nao_aceitam_so_o_rg(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    por_nome = {linha.nome: linha for linha in linhas_da_fonte}
    guiana = por_nome["Guyana"]
    assert "ID card" in guiana.notas  # a nota fala em RG, mas só para a fronteira
    resultado = dicionario_real.classificar_rotulo(guiana.rotulo, guiana.notas)
    assert resultado.categoria is CategoriaDeVisto.ISENTO
    assert resultado.aceita_rg is False

    venezuela = por_nome["Venezuela"]
    assert venezuela.notas == ""
    resultado = dicionario_real.classificar_rotulo(venezuela.rotulo, venezuela.notas)
    assert resultado.categoria is CategoriaDeVisto.ISENTO
    assert resultado.aceita_rg is False


def test_os_oito_sao_isentos_com_o_rotulo_freedom_of_movement(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    linhas = [linha for linha in linhas_da_fonte if linha.rotulo == "Freedom of Movement"]
    assert len(linhas) == 8
    assert all("ID card" in linha.notas for linha in linhas)
    for linha in linhas:
        resultado = dicionario_real.classificar_rotulo(linha.rotulo, linha.notas)
        assert resultado.categoria is CategoriaDeVisto.ISENTO


def test_freedom_of_movement_sem_a_frase_fica_isento_sem_rg_e_avisa_no_log(
    dicionario_real: Dicionario, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="farol.vistos"):
        resultado = dicionario_real.classificar_rotulo("Freedom of Movement", "Sem frase nenhuma.")
    assert resultado.categoria is CategoriaDeVisto.ISENTO
    assert resultado.aceita_rg is False
    assert [r for r in caplog.records if r.name == "farol.vistos" and "ID card" in r.getMessage()]


def test_nenhum_outro_rotulo_da_fixture_afirma_o_rg(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    for linha in linhas_da_fonte:
        if linha.rotulo != "Freedom of Movement":
            assert not dicionario_real.classificar_rotulo(linha.rotulo, linha.notas).aceita_rg
