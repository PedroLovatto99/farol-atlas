"""Expressões como "demais regiões do país" são o nível do país inteiro, não uma região."""

import pytest

from farol.dominio import NivelAlerta, e_nivel_do_pais, separar_nivel_do_pais

E, N, NORM = NivelAlerta.EVITAR, NivelAlerta.NAO_VIAJAR, NivelAlerta.NORMALIZADA


@pytest.mark.parametrize(
    "nome",
    [
        "demais regiões do país",
        "Demais regiões do país",
        "DEMAIS REGIÕES DO PAÍS",
        "demais regioes do pais",
        "demais regiões",
        "As demais regiões do país",
        "demais áreas do país",
        "demais regiões do território",
        "restante do país",
        "o restante do país",
        "Restante do território",
        "resto do país",
        "o resto do país",
        "todo o país",
        "Todo o país",
        "em todo o país",
        "todo o território",
        "país inteiro",
        "o país inteiro",
        "território inteiro",
        "  demais   regiões \n do país. ",
        "Demais regiões do país:",
        "(demais regiões do país)",
    ],
)
def test_expressao_que_e_o_pais_inteiro(nome: str) -> None:
    assert e_nivel_do_pais(nome) is True


@pytest.mark.parametrize(
    "nome",
    [
        "Sul do Líbano",
        "Faixa de Gaza",
        "Cisjordânia",
        "Norte do país",
        "Todo o sul do país",
        "Todo o sul",
        "Demais regiões da fronteira com Israel",
        "Demais regiões do norte",
        "Restante da província de Idlib",
        "Resto do mundo",
        "Regiões do país",
        "País vizinho",
        "",
        "   ",
    ],
)
def test_nome_de_regiao_de_verdade_nao_e_o_pais_inteiro(nome: str) -> None:
    assert e_nivel_do_pais(nome) is False


# --------------------------------------------------------------------------- separação
def test_demais_regioes_viram_o_nivel_do_pais_quando_ele_nao_veio() -> None:
    nivel, regioes = separar_nivel_do_pais(
        None, [("Sul do Líbano", N), ("demais regiões do país", E)]
    )

    assert nivel is E
    assert regioes == [("Sul do Líbano", N)]


def test_so_a_expressao_do_pais_inteiro_sem_nenhuma_regiao_nomeada() -> None:
    assert separar_nivel_do_pais(None, [("todo o território", N)]) == (N, [])


def test_nivel_do_pais_ja_informado_e_regioes_nomeadas_ficam_como_estao() -> None:
    regioes = [("Sul do Líbano", N)]

    assert separar_nivel_do_pais(E, regioes) == (E, regioes)
    assert separar_nivel_do_pais(None, regioes) == (None, regioes)  # alerta só regional
    assert separar_nivel_do_pais(None, []) == (None, [])


def test_nivel_do_pais_e_expressao_iguais_nao_mudam_nada() -> None:
    assert separar_nivel_do_pais(E, [("restante do país", E)]) == (E, [])


@pytest.mark.parametrize(
    ("do_pais", "da_expressao", "esperado"),
    [
        (E, N, N),
        (N, E, N),  # na dúvida vale o mais grave: nunca esconde um "não viaje"
        (NORM, E, E),
        (E, NORM, E),
        (None, NORM, NORM),
    ],
)
def test_conflito_entre_o_nivel_do_pais_e_a_expressao_fica_com_o_mais_grave(
    do_pais: NivelAlerta | None, da_expressao: NivelAlerta, esperado: NivelAlerta
) -> None:
    nivel, regioes = separar_nivel_do_pais(do_pais, [("demais regiões do país", da_expressao)])

    assert nivel is esperado
    assert regioes == []


def test_varias_expressoes_ficam_com_a_mais_grave_e_a_ordem_das_regioes_se_mantem() -> None:
    nivel, regioes = separar_nivel_do_pais(
        None,
        [
            ("Norte", E),
            ("restante do país", E),
            ("Sul", N),
            ("todo o país", N),
        ],
    )

    assert nivel is N
    assert regioes == [("Norte", E), ("Sul", N)]


def test_separar_duas_vezes_da_o_mesmo_resultado() -> None:
    primeira = separar_nivel_do_pais(None, [("Sul do Líbano", N), ("demais regiões do país", E)])

    assert separar_nivel_do_pais(*primeira) == primeira
