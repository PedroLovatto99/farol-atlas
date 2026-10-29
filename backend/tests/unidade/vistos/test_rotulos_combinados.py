"""Rótulos combinados e regra geral de categoria, sobre as linhas reais da fixture."""

import pytest

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.vistos.dicionario import Dicionario
from farol.vistos.fonte import LinhaDaFonte

ISENTO = CategoriaDeVisto.ISENTO
NA_CHEGADA = CategoriaDeVisto.VISTO_NA_CHEGADA
ELETRONICA = CategoriaDeVisto.AUTORIZACAO_ELETRONICA
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO

# Os 5 combinados da fixture: o rótulo da fonte e os países que o têm
COMBINADOS = [
    ("eVisa / Visa on arrival", ["Bahrain", "Egypt", "Cambodia"], ELETRONICA),
    ("Online Visa / Visa on arrival", ["Burundi", "Nepal"], ELETRONICA),
    ("Visa not required / eVisa", ["Oman", "Tajikistan"], ELETRONICA),
    ("ETA / Visa on arrival", ["Sri Lanka"], ELETRONICA),
    ("Visa not required / e-VOA", ["Indonesia"], ELETRONICA),
]


def _linha(linhas: list[LinhaDaFonte], nome: str) -> LinhaDaFonte:
    (linha,) = [linha for linha in linhas if linha.nome == nome]
    return linha


@pytest.mark.parametrize(("rotulo", "paises", "esperada"), COMBINADOS)
def test_combinados_da_fixture_valem_a_categoria_mais_exigente(
    dicionario_real: Dicionario,
    linhas_da_fonte: list[LinhaDaFonte],
    rotulo: str,
    paises: list[str],
    esperada: CategoriaDeVisto,
) -> None:
    for pais in paises:
        linha = _linha(linhas_da_fonte, pais)
        assert linha.rotulo == rotulo
        resultado = dicionario_real.classificar_rotulo(linha.rotulo)
        assert resultado.categoria is esperada, pais
        assert resultado.motivo_outra is None
        assert resultado.rotulo_para_revisao is None


def test_a_fixture_tem_exatamente_cinco_rotulos_combinados(
    linhas_da_fonte: list[LinhaDaFonte],
) -> None:
    combinados = {linha.rotulo for linha in linhas_da_fonte if " / " in linha.rotulo}
    assert combinados == {rotulo for rotulo, _, _ in COMBINADOS}


@pytest.mark.parametrize(
    ("pais", "esperada"),
    [
        ("Australia", EXIGIDO),  # "Online visa required": visto completo pedido online
        ("Liberia", ELETRONICA),  # "e-VOA": pedido online simplificado
        ("Indonesia", ELETRONICA),
        ("Samoa", NA_CHEGADA),  # "Entry permit on arrival": obtido na chegada
        ("Solomon Islands", NA_CHEGADA),  # "Free Visitor's permit on arrival"
        ("Burundi", ELETRONICA),
        ("Nepal", ELETRONICA),
    ],
)
def test_regra_geral_de_categoria(
    dicionario_real: Dicionario,
    linhas_da_fonte: list[LinhaDaFonte],
    pais: str,
    esperada: CategoriaDeVisto,
) -> None:
    rotulo = _linha(linhas_da_fonte, pais).rotulo
    assert dicionario_real.classificar_rotulo(rotulo).categoria is esperada


def test_visto_exigido_com_entrada_recusada_vira_outra_situacao(
    dicionario_real: Dicionario,
) -> None:
    resultado = dicionario_real.classificar_rotulo("Visa required / Admission refused")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "visa required / admission refused"


def test_isento_com_rotulo_desconhecido_nunca_e_isento(dicionario_real: Dicionario) -> None:
    resultado = dicionario_real.classificar_rotulo("Visa not required / Rótulo Inventado")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "visa not required / rótulo inventado"


def test_santa_helena_ascensao_e_tristao_da_cunha_ficam_em_outra_situacao(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    """Três linhas para o código `SH`: a parte "Permission required" leva o território todo."""
    linhas = [
        _linha(linhas_da_fonte, nome)
        for nome in ("Saint Helena", "Ascension Island", "Tristan da Cunha")
    ]
    assert {dicionario_real.ligar_nome(linha.nome).codigo for linha in linhas} == {"SH"}
    assert [linha.rotulo for linha in linhas] == [
        "Visa not required",
        "eVisa",
        "Permission required",
    ]
    rotulo_das_partes = " / ".join(linha.rotulo for linha in linhas)
    resultado = dicionario_real.classificar_rotulo(rotulo_das_partes)
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO
    assert resultado.rotulo_para_revisao is None
