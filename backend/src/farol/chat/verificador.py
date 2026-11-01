"""Verificador de prosa (D5): o texto do modelo só passa se o código consegue sustentá-lo.

Roda contra o que esta pergunta realmente entregou ao modelo (os trechos dos alertas, a pergunta e
os países achados pelo código). Descarta a prosa que:
- chama de segurança ("seguro", "tranquilo", "sem riscos", "pode viajar") ou recomenda por conta
  própria ("recomendo", "vale a pena");
- traz URL, HTML ou link de Markdown (links só existem nas citações, montadas pelo código);
- cita um país que não está nos dados desta resposta (nos trechos, na pergunta ou nos países
  achados): é o que pega o modelo completando uma lista "de cabeça";
- traz um número (telefone, data, prazo) que não aparece nos trechos nem na pergunta. Números por
  extenso contam como algarismos ("seis" e "6" são o mesmo número, "vinte e um" é 21).

Quem recebe a violação decide o que fazer; no chat, a resposta cai na contingência, só com as
citações que o código monta.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from farol.chat.ferramentas import TrechoUsado
from farol.chat.protocolos import PaisEncontrado, ResolvedorDePaises


@dataclass(frozen=True)
class Violacao:
    regra: str
    detalhe: str


_SEGURANCA = re.compile(
    r"(?<![a-z0-9])(?:seguros?|seguras?|tranquil[oa]s?|sem riscos?|podem? viajar|"
    r"recomendo|valem? a pena)(?![a-z0-9])"
)
_LINK_OU_HTML = re.compile(r"https?://|www\.|</?[a-z][^>]*>|\]\(")
_NUMERO = re.compile(r"\d+")

_POR_EXTENSO = {
    palavra: valor
    for valor, palavras in {
        0: "zero", 1: "um uma", 2: "dois duas", 3: "tres", 4: "quatro", 5: "cinco", 6: "seis",
        7: "sete", 8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze", 13: "treze",
        14: "catorze quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito",
        19: "dezenove", 20: "vinte", 30: "trinta", 40: "quarenta", 50: "cinquenta",
        60: "sessenta", 70: "setenta", 80: "oitenta", 90: "noventa", 100: "cem cento",
        200: "duzentos duzentas", 300: "trezentos trezentas", 400: "quatrocentos quatrocentas",
        500: "quinhentos quinhentas", 600: "seiscentos seiscentas", 700: "setecentos setecentas",
        800: "oitocentos oitocentas", 900: "novecentos novecentas",
    }.items()
    for palavra in palavras.split()
}  # fmt: skip
_PALAVRA_DE_NUMERO = "(?:" + "|".join(sorted(_POR_EXTENSO, key=len, reverse=True)) + ")"
# "vinte e um", "cento e vinte e tres": partes ligadas por "e" somam
_EXTENSO = re.compile(
    rf"(?<![a-z0-9]){_PALAVRA_DE_NUMERO}(?:\s+e\s+{_PALAVRA_DE_NUMERO})*(?![a-z0-9])"
)


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.lower().split())


def _numeros(texto: str, *, um_sozinho: bool) -> list[str]:
    """Os números do texto em algarismos, os por extenso convertidos.

    "um"/"uma" sozinhos só contam com `um_sozinho` (nos dados): na prosa são quase sempre artigo.
    """
    numeros = _NUMERO.findall(texto)
    for achado in _EXTENSO.finditer(_normalizar(texto)):
        partes = achado.group(0).split()[::2]
        if len(partes) == 1 and partes[0] in ("um", "uma") and not um_sozinho:
            continue
        numeros.append(str(sum(_POR_EXTENSO[p] for p in partes)))
    return numeros


def _codigos(resolvedor: ResolvedorDePaises, texto: str) -> set[str]:
    achados = resolvedor.resolver(texto)
    return {p.codigo for p in achados.encontrados} | {
        p.codigo for grupo in achados.ambiguos for p in grupo
    }


def verificar_prosa(
    texto: str,
    *,
    trechos: Sequence[TrechoUsado],
    pergunta: str,
    paises: Sequence[PaisEncontrado],
    resolvedor: ResolvedorDePaises,
) -> Violacao | None:
    """A primeira regra violada pela prosa, ou nulo se ela se sustenta nos dados."""
    if achado := _SEGURANCA.search(_normalizar(texto)):
        return Violacao("seguranca_ou_recomendacao", f"trecho {achado.group(0)!r}")
    if achado := _LINK_OU_HTML.search(texto.lower()):
        return Violacao("link_ou_html", f"trecho {achado.group(0)!r}")

    base = " ".join([pergunta, *(t.trecho for t in trechos)])
    permitidos = {p.codigo for p in paises} | _codigos(resolvedor, base)
    achados = resolvedor.resolver(texto)
    citados = {p.codigo: p.nome for p in achados.encontrados}
    citados |= {p.codigo: p.nome for grupo in achados.ambiguos for p in grupo}
    fora = [nome for codigo, nome in citados.items() if codigo not in permitidos]
    if fora:
        return Violacao("pais_fora_dos_dados", ", ".join(fora))

    conhecidos = set(_numeros(base, um_sozinho=True))
    estranhos = [n for n in _numeros(texto, um_sozinho=False) if n not in conhecidos]
    if estranhos:
        return Violacao("numero_fora_dos_dados", ", ".join(estranhos))
    return None
