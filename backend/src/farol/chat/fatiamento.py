"""Divide o texto de um alerta em trechos `[inicio, fim)` (contracts/indexacao-e-comandos.md §2).

O trecho que o chat mostra é sempre `alerta.texto[inicio:fim]`; nada é copiado. Por isso os
intervalos são calculados sobre o próprio `texto`, e o `html_corpo` só serve para saber onde ficam
os parágrafos (`p`, `li`, títulos).

Regras: parágrafos agrupados até cerca de 1.000 caracteres (nunca mais de 1.600), com a
sobreposição de um parágrafo entre trechos vizinhos; um parágrafo que não se localiza no texto, ou o
texto solto fora dos parágrafos, é fatiado por frases; um pedaço sem pontuação é cortado no espaço.
Nenhum trecho começa ou termina no meio de uma palavra, e nada do texto fica de fora.
"""

import re

from bs4 import BeautifulSoup

ALVO_DE_CARACTERES = 1000
MAXIMO_DE_CARACTERES = 1600
SOBREPOSICAO_MAXIMA = 400  # um parágrafo maior que isto não é repetido no trecho seguinte

_BLOCOS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "td", "th", "pre"]
_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+")

Intervalo = tuple[int, int]


def _blocos_do_html(html_corpo: str) -> list[str]:
    """O texto de cada bloco "folha" (sem outro bloco dentro), como a coleta monta o `texto`."""
    sopa = BeautifulSoup(html_corpo, "html.parser")
    blocos = []
    for elemento in sopa.find_all(_BLOCOS):
        if elemento.find(_BLOCOS):
            continue
        texto = " ".join(elemento.get_text(" ", strip=True).split())
        if texto:
            blocos.append(texto)
    return blocos


def _aparar(texto: str, inicio: int, fim: int) -> Intervalo | None:
    while inicio < fim and texto[inicio].isspace():
        inicio += 1
    while fim > inicio and texto[fim - 1].isspace():
        fim -= 1
    return (inicio, fim) if fim > inicio else None


def _cortar_no_espaco(texto: str, inicio: int, fim: int) -> list[Intervalo]:
    """Pedaços de até `ALVO_DE_CARACTERES`, cortados no último espaço antes do limite."""
    pedacos = []
    while fim - inicio > ALVO_DE_CARACTERES:
        corte = texto.rfind(" ", inicio, inicio + ALVO_DE_CARACTERES)
        if corte <= inicio:
            corte = inicio + ALVO_DE_CARACTERES  # palavra gigante: não há espaço onde cortar
        if (pedaco := _aparar(texto, inicio, corte)) is not None:
            pedacos.append(pedaco)
        inicio = corte
    if (pedaco := _aparar(texto, inicio, fim)) is not None:
        pedacos.append(pedaco)
    return pedacos


def _por_frases(texto: str, inicio: int, fim: int) -> list[Intervalo]:
    """Frases de `texto[inicio:fim]`, juntadas até o alvo; frase maior que o alvo é cortada."""
    frases: list[Intervalo] = []
    ponta = inicio
    for corte in [*_FIM_DE_FRASE.finditer(texto, inicio, fim)]:
        frases.append((ponta, corte.start()))
        ponta = corte.end()
    frases.append((ponta, fim))

    segmentos: list[Intervalo] = []
    for a, b in frases:
        if (frase := _aparar(texto, a, b)) is None:
            continue
        if frase[1] - frase[0] > ALVO_DE_CARACTERES:
            segmentos.extend(_cortar_no_espaco(texto, *frase))
        else:
            segmentos.append(frase)
    return segmentos


def _segmentos(texto: str, html_corpo: str | None) -> list[Intervalo]:
    """As unidades que o fatiamento agrupa: parágrafos achados no texto e frases do resto."""
    achados: list[Intervalo] = []
    cursor = 0
    for bloco in _blocos_do_html(html_corpo) if html_corpo else []:
        posicao = texto.find(bloco, cursor)
        if posicao >= 0:
            achados.append((posicao, posicao + len(bloco)))
            cursor = posicao + len(bloco)

    segmentos: list[Intervalo] = []
    ponta = 0
    for inicio, fim in [*achados, (len(texto), len(texto))]:
        if inicio > ponta:
            segmentos.extend(_por_frases(texto, ponta, inicio))  # texto fora dos parágrafos
        if fim - inicio > ALVO_DE_CARACTERES:
            segmentos.extend(_por_frases(texto, inicio, fim))
        elif fim > inicio:
            segmentos.append((inicio, fim))
        ponta = fim
    return segmentos


def fatiar(texto: str, html_corpo: str | None = None) -> list[Intervalo]:
    """Os trechos `[inicio, fim)` do `texto`, na ordem; vazio se o texto não tem nada escrito."""
    segmentos = _segmentos(texto, html_corpo)
    trechos: list[Intervalo] = []
    primeiro = 0
    repete = False  # o primeiro parágrafo já esteve no trecho anterior: o trecho precisa avançar
    while primeiro < len(segmentos):
        ultimo = primeiro + 1 if repete else primeiro
        while (
            ultimo + 1 < len(segmentos)
            and segmentos[ultimo + 1][1] - segmentos[primeiro][0] <= ALVO_DE_CARACTERES
        ):
            ultimo += 1
        trechos.append((segmentos[primeiro][0], segmentos[ultimo][1]))
        if ultimo + 1 >= len(segmentos):
            break
        primeiro, repete = _proximo_primeiro(segmentos, primeiro, ultimo)
    return trechos


def _proximo_primeiro(segmentos: list[Intervalo], primeiro: int, ultimo: int) -> tuple[int, bool]:
    """Onde começa o trecho seguinte e se ele repete o último parágrafo do atual (se couber)."""
    if ultimo == primeiro:
        return ultimo + 1, False  # o trecho era um parágrafo só: nada a repetir
    repetido = segmentos[ultimo]
    cabe = repetido[1] - repetido[0] <= SOBREPOSICAO_MAXIMA
    if cabe and segmentos[ultimo + 1][1] - repetido[0] <= MAXIMO_DE_CARACTERES:
        return ultimo, True
    return ultimo + 1, False
