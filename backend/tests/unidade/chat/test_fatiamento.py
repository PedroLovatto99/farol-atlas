"""Fatiamento do texto de um alerta em trechos `[inicio, fim)`.

O que o chat mostra em "Ver trecho" é `alerta.texto[inicio:fim]`, então os intervalos precisam cair
dentro do texto, não partir palavras e, juntos, cobrir tudo o que há de texto no alerta.
"""

import itertools
import re

import pytest
from tests.falsos_chat import ler_alertas_json

from farol.chat.fatiamento import ALVO_DE_CARACTERES, MAXIMO_DE_CARACTERES, fatiar

ALERTAS = ler_alertas_json()


def _html(*paragrafos: str) -> tuple[str, str]:
    """O texto como a coleta o monta (palavras separadas por um espaço) e o HTML de origem."""
    html = "<div>" + "".join(f"<p>{p}</p>\n" for p in paragrafos) + "</div>"
    return " ".join(" ".join(paragrafos).split()), html


def _paragrafo(n: int, palavras: int = 22) -> str:
    return f"Parágrafo {n}. " + " ".join(f"palavra{n}x{i}" for i in range(palavras)) + "."


def _confere_invariantes(texto: str, trechos: list[tuple[int, int]]) -> None:
    assert trechos, "todo texto não vazio vira pelo menos um trecho"
    anterior = (-1, 0)
    for inicio, fim in trechos:
        assert 0 <= inicio < fim <= len(texto)
        assert fim - inicio <= MAXIMO_DE_CARACTERES
        trecho = texto[inicio:fim]
        assert trecho == trecho.strip() and trecho
        # não parte palavra: antes do início e depois do fim há espaço (ou o limite do texto)
        assert inicio == 0 or texto[inicio - 1].isspace()
        assert fim == len(texto) or texto[fim].isspace()
        assert inicio > anterior[0] and fim > anterior[1]  # sempre avança
        anterior = (inicio, fim)
    # sem buracos: o que fica entre um trecho e o seguinte (ou antes do primeiro) é só espaço
    coberto = 0
    for inicio, fim in sorted(trechos):
        assert texto[coberto:inicio].strip() == "", "sobrou texto sem trecho"
        coberto = max(coberto, fim)
    assert texto[coberto:].strip() == ""


def test_texto_curto_vira_um_trecho_so() -> None:
    texto, html = _html("Um aviso curto.", "Outro aviso curto.")
    assert fatiar(texto, html) == [(0, len(texto))]


def test_texto_vazio_nao_tem_trecho() -> None:
    assert fatiar("", None) == []
    assert fatiar("   ", "<p>   </p>") == []


def test_agrupa_paragrafos_ate_o_alvo_e_repete_um_na_virada() -> None:
    paragrafos = [_paragrafo(n) for n in range(12)]  # ~280 caracteres cada
    texto, html = _html(*paragrafos)

    trechos = fatiar(texto, html)

    _confere_invariantes(texto, trechos)
    assert len(trechos) > 1
    assert all(fim - inicio <= ALVO_DE_CARACTERES + 400 for inicio, fim in trechos)
    for (_, fim_anterior), (inicio, _) in itertools.pairwise(trechos):
        # sobreposição de exatamente um parágrafo: o seguinte começa no início de um parágrafo
        # que já estava no trecho anterior
        assert inicio < fim_anterior
        assert texto[inicio:].startswith("Parágrafo ")


def test_cada_trecho_e_a_fatia_do_texto() -> None:
    texto, html = _html(*[_paragrafo(n) for n in range(8)])
    for inicio, fim in fatiar(texto, html):
        assert texto[inicio:fim].startswith("Parágrafo ")
        assert texto[inicio:fim].endswith(".")


def test_html_que_nao_bate_com_o_texto_cai_em_frases() -> None:
    frases = [f"Esta é a frase número {n} do aviso e ela segue por um tempo." for n in range(60)]
    texto = " ".join(frases)
    html = "<p>nada a ver com o texto</p><p>outra coisa que não está lá</p>"

    trechos = fatiar(texto, html)

    _confere_invariantes(texto, trechos)
    assert len(trechos) > 1
    for _, fim in trechos:
        assert texto[fim - 1] == "."  # terminam em fim de frase


def test_sem_html_fatia_por_frases() -> None:
    texto = " ".join(f"Frase {n} do aviso, sem nenhum HTML por trás." for n in range(80))
    trechos = fatiar(texto, None)
    _confere_invariantes(texto, trechos)
    assert len(trechos) > 1


def test_paragrafo_maior_que_o_maximo_e_cortado_em_frases() -> None:
    longo = " ".join(f"Frase longa número {n} com algum conteúdo útil." for n in range(90))
    assert len(longo) > MAXIMO_DE_CARACTERES
    texto, html = _html("Abertura curta.", longo, "Fecho curto.")

    trechos = fatiar(texto, html)

    _confere_invariantes(texto, trechos)
    assert len(trechos) >= 3


def test_texto_sem_pontuacao_e_cortado_no_espaco() -> None:
    texto = " ".join(f"palavra{n}" for n in range(1200))
    trechos = fatiar(texto, None)
    _confere_invariantes(texto, trechos)
    assert len(trechos) > 1


def test_texto_fora_dos_paragrafos_do_html_tambem_e_coberto() -> None:
    """Texto solto (sem `<p>`) entre parágrafos não pode ficar sem trecho."""
    texto = "Primeiro parágrafo aqui. Texto solto no meio da página. Último parágrafo aqui."
    html = (
        "<div><p>Primeiro parágrafo aqui.</p>Texto solto no meio da página."
        "<p>Último parágrafo aqui.</p></div>"
    )
    _confere_invariantes(texto, fatiar(texto, html))


def test_lista_com_o_cabecalho_fica_no_mesmo_trecho() -> None:
    """Item de lista não se separa do cabeçalho dele ("Não viajar para:" e os países)."""
    cabecalho = "Não viajar para:"
    itens = ["Irã", "Israel", "Sul do Líbano", "Palestina (Faixa de Gaza)", "Iémen"]
    html = (
        "<div><p>Introdução do aviso consular.</p><ul><li><b>Não viajar</b><b> para: </b></li>"
        "<ul>" + "".join(f"<li>{i}</li>" for i in itens) + "</ul></ul></div>"
    )
    texto = " ".join(["Introdução do aviso consular.", cabecalho, *itens])
    trechos = fatiar(texto, html)
    _confere_invariantes(texto, trechos)
    assert len(trechos) == 1


@pytest.mark.parametrize("alerta", ALERTAS, ids=[a["id"] for a in ALERTAS])
def test_alertas_reais_do_banco_respeitam_as_regras(alerta: dict[str, str]) -> None:
    texto = alerta["texto"]
    trechos = fatiar(texto, alerta["html_corpo"])

    _confere_invariantes(texto, trechos)
    esperado_no_minimo = len(texto) // MAXIMO_DE_CARACTERES
    assert len(trechos) >= max(1, esperado_no_minimo)


def test_oriente_medio_primeiro_trecho_traz_as_duas_listas_inteiras() -> None:
    oriente = next(a for a in ALERTAS if a["titulo"].startswith("Alerta Consular. Oriente"))
    texto = oriente["texto"]
    inicio, fim = fatiar(texto, oriente["html_corpo"])[0]
    primeiro = texto[inicio:fim]
    assert "Não viajar para:" in primeiro and "Palestina (Faixa de Gaza)" in primeiro
    assert "Evitar viagens não essenciais" in primeiro and "Arábia Saudita*" in primeiro
    assert re.search(r"conexões aéreas\.", primeiro)
