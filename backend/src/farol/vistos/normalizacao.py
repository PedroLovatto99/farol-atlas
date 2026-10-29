"""Normalização do texto da Wikipédia e das chaves dos dicionários.

As mesmas funções servem aos dois lados (texto da fonte e chaves dos arquivos YAML), para que a
consulta nunca dependa de espaço, apóstrofo ou, nos rótulos, barra escritos de outro jeito. Elas
devolvem texto puro: nada aqui interpreta HTML (`contracts/dicionario-de-rotulos.md`,
"Normalização").
"""

import re

_BLOCO_SUP = re.compile(r"[ \t]*<sup\b[^>]*>.*?</sup\s*>", flags=re.IGNORECASE | re.DOTALL)
_ESPACO_QUE_NAO_QUEBRA_LINHA = re.compile(r"[^\S\r\n]")
_CARACTERES_INVISIVEIS = re.compile("[\u200b-\u200d\u2060\ufeff]")
# [2], [ 374 ], [Note 4]; leva junto o espaço que vem antes ("word [2]." -> "word.")
_MARCA_DE_REFERENCIA = re.compile(r" *\[\s*(?:Note\s+)?\d+\s*\]", flags=re.IGNORECASE)
# só conta a barra isolada: "https://" e a de fechar tag ("</b>") ficam de fora
_BARRA = re.compile(r"(?<![/<]) *(?<![/<])/(?!/) *")
_TIPOGRAFICOS = str.maketrans(
    {"’": "'", "‘": "'", "‛": "'", "ʼ": "'", "´": "'", "“": '"', "”": '"', "„": '"'}
)


def _normalizar(texto: str, *, barra: bool) -> str:
    texto = _BLOCO_SUP.sub("", texto)
    texto = _CARACTERES_INVISIVEIS.sub("", texto)
    texto = _ESPACO_QUE_NAO_QUEBRA_LINHA.sub(" ", texto)  # inclui o espaço não separável
    texto = _MARCA_DE_REFERENCIA.sub("", texto)
    texto = texto.translate(_TIPOGRAFICOS)
    if barra:
        texto = _BARRA.sub(" / ", texto)
    linhas = (" ".join(linha.split()) for linha in re.split(r"\r\n|\r|\n", texto))
    return "\n".join(linha for linha in linhas if linha)


def normalizar(texto: str) -> str:
    """Texto limpo, com a caixa e a pontuação da fonte preservadas (é o que o painel mostra).

    Remove as marcas de referência, troca o espaço não separável, colapsa espaços e uniformiza
    aspas e apóstrofos. A barra não é mexida: observações, nomes e prazos ficam como na fonte.
    Cada linha do texto é tratada à parte e as linhas vazias somem; é assim que os itens de uma
    lista de notas ficam um por linha.
    """
    return _normalizar(texto, barra=False)


def normalizar_rotulo(texto: str) -> str:
    """Como `normalizar`, e ainda uniformiza a barra: `A/B`, `A /B` e `A/ B` viram `A / B`.

    Só os rótulos de situação usam a barra como separador de partes.
    """
    return _normalizar(texto, barra=True)


def chave_de_consulta(texto: str) -> str:
    """Chave de consulta dos nomes: o texto normalizado em caixa baixa (`casefold`)."""
    return normalizar(texto).casefold()


def chave_de_rotulo(texto: str) -> str:
    """Chave de consulta dos rótulos: normalizada com a barra uniformizada, em caixa baixa."""
    return normalizar_rotulo(texto).casefold()
