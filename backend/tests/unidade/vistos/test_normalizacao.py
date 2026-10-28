"""Normalização do texto da Wikipédia e das chaves dos dicionários (uma função só para os dois)."""

import pytest

from farol.vistos.normalizacao import (
    chave_de_consulta,
    chave_de_rotulo,
    normalizar,
    normalizar_rotulo,
)


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Visa required[2]", "Visa required"),
        ("Visa required [2]", "Visa required"),
        ("Visa required [ 374 ]", "Visa required"),
        ("eVisa[8][9]", "eVisa"),
        ("eVisa [ 8 ] [ 9 ]", "eVisa"),
        ("18[Note 4] of the 33 border crossings", "18 of the 33 border crossings"),
        ("Visa required<sup>[2]</sup>", "Visa required"),
        ('Visa required<sup class="reference" id="x">[ 2 ]</sup>', "Visa required"),
        ("90 days[27]", "90 days"),
    ],
)
def test_remove_marcas_de_referencia(bruto: str, esperado: str) -> None:
    assert normalizar(bruto) == esperado


def test_marca_colada_na_pontuacao_nao_deixa_espaco_antes_dela() -> None:
    assert normalizar("Schengen Area [27].") == "Schengen Area."


def test_troca_espaco_nao_separavel_e_colapsa_espacos() -> None:
    assert normalizar("Visa\xa0not   required  ") == "Visa not required"
    assert normalizar("  e-Visa\xa0: Visitors  must   arrive ") == "e-Visa : Visitors must arrive"


def test_uniformiza_apostrofos_e_aspas_tipograficas() -> None:
    assert normalizar("Free Visitor’s permit on arrival") == "Free Visitor's permit on arrival"
    assert normalizar("Côte d’Ivoire") == "Côte d'Ivoire"
    assert normalizar("‘a’ e “b”") == "'a' e \"b\""


@pytest.mark.parametrize(
    "bruto",
    [
        "eVisa/Visa on arrival",
        "eVisa /Visa on arrival",
        "eVisa/ Visa on arrival",
        "eVisa / Visa on arrival",
    ],
)
def test_rotulo_uniformiza_a_barra(bruto: str) -> None:
    assert normalizar_rotulo(bruto) == "eVisa / Visa on arrival"


@pytest.mark.parametrize(
    "texto",
    [
        "15/30 pounds sterling (yacht/ship passenger)",
        "and/or",
        "14 days/30 days",
        "https://exemplo.org/a",
        "Brazil/Argentina /Chile",
    ],
)
def test_fora_dos_rotulos_a_barra_fica_como_na_fonte(texto: str) -> None:
    """Observações, nomes e prazos não têm a barra mexida (só espaços e marcas de referência)."""
    assert normalizar(texto) == texto


def test_fora_dos_rotulos_so_a_limpeza_de_espacos_e_marcas_vale_na_barra() -> None:
    assert normalizar("15/30  pounds sterling[4]") == "15/30 pounds sterling"


def test_rotulo_mantem_o_resto_da_normalizacao() -> None:
    assert normalizar_rotulo("Free Visitor’s  permit[3]") == "Free Visitor's permit"
    assert normalizar_rotulo("<b>negrito</b>") == "<b>negrito</b>"
    assert normalizar_rotulo("https://exemplo.org") == "https://exemplo.org"


def test_mantem_a_caixa_do_texto_exibido() -> None:
    assert normalizar("Visa Not Required") == "Visa Not Required"


def test_quebras_de_linha_separam_itens_e_linhas_vazias_somem() -> None:
    assert normalizar("  primeira  \n\n  segunda\xa0linha \n") == "primeira\nsegunda linha"


def test_texto_vazio_continua_vazio() -> None:
    assert normalizar("") == ""
    assert normalizar(" \xa0 [3] ") == ""


def test_html_que_nao_e_marca_de_referencia_fica_como_texto() -> None:
    assert normalizar("<b>negrito</b>") == "<b>negrito</b>"


def test_chave_de_consulta_usa_casefold_sem_mudar_o_texto_exibido() -> None:
    exibido = normalizar("Visa Not Required[3]")
    assert exibido == "Visa Not Required"
    assert chave_de_consulta("Visa Not Required[3]") == "visa not required"
    assert chave_de_consulta("Straße") == "strasse"
    assert chave_de_consulta("Bosnia/Herzegovina") == "bosnia/herzegovina"


def test_chave_de_rotulo_uniformiza_a_barra_e_usa_casefold() -> None:
    assert chave_de_rotulo("eVisa/Visa on arrival") == "evisa / visa on arrival"
    assert chave_de_rotulo("Visa Not Required[3]") == "visa not required"
