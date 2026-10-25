"""Extrai endereço e telefone de plantão das páginas de um posto, de melhor esforço.

O gov.br não tem formato fixo para essas informações (research.md, R1): cada posto monta as suas
abas do jeito que quer. Por isso os extratores só aceitam o que é inequívoco e devolvem nulo no
resto. Mostrar um telefone errado numa emergência é pior do que não mostrar nenhum.

- **Endereço**: o bloco que vem depois de um título "Endereço" (ou um `<address>`), até o próximo
  título (Localização, Telefone, E-mail...).
- **Telefone de plantão**: o número que aparece logo depois de "plantão" ou "plantonista" na mesma
  frase, desde que a frase não seja sobre o plantão do Ministério em Brasília, que não é o do posto.
"""

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from farol.coleta.texto import sem_acentos

_ROTULO_DO_ENDERECO = re.compile(r"^Endere[çc]o\b(?P<resto>.*)$", re.IGNORECASE)
_ENDERECO_QUE_NAO_E_DE_RUA = re.compile(
    r"^\W*(eletr[ôo]nico|de\s+e-?mail|de\s+correio|web|internet)\b", re.IGNORECASE
)
# Linhas que encerram o bloco do endereço: o próximo título ou rótulo ("Telefone", "Instagram:")
_FIM_DO_ENDERECO = re.compile(
    r"^(localiza[çc][ãa]o|telefones?|tel\b|fax|e-?mail|contatos?|hor[áa]rios?|como\s+chegar|"
    r"mapa|ver\s+no|google|site|whatsapp|fale)\b",
    re.IGNORECASE,
)
# "Embaixada do Brasil na Índia e no Butão": o nome da representação não é parte do endereço
_NOME_DA_REPRESENTACAO = re.compile(
    r"^(embaixada|consulado|vice-consulado|escrit[óo]rio)\b.*\bbrasil\b", re.IGNORECASE
)
_SEM_NUMERO_DE_RUA = re.compile(r"\bs\s*/\s*n\b|sem\s+n[úu]mero", re.IGNORECASE)
# Menus do site, avisos e frases que aparecem perto do endereço (vistos na coleta real) e o
# endereço da sede do Itamaraty em Brasília, que não é o de nenhum posto
_NAO_E_ENDERECO = re.compile(
    r"\b(servi[çc]os\s+consulares|informa[çc][õo]es\s+gerais|matr[ií]cula|plant[ãa]o|"
    r"composi[çc][ãa]o|organograma|quem\s+[ée]\s+quem|gabinete|secretaria-geral|"
    r"processo\s+seletivo|edital|bolsa|contratos|licita[çc][õo]es|not[ií]cias|clique|"
    r"maiores\s+informa[çc][õo]es|em\s+caso\s+de|por\s+favor|atendimento|hor[áa]rio|"
    r"agendamento|n[ãa]o\s+possui)\b"
    r"|^(o|a|os|as)\s+(consulado|embaixada)\b"
    r"|setor\s+banc[áa]rio\s+sul|esplanada\s+dos\s+minist[ée]rios|bras[ií]lia\s*[-,/]?\s*df",
    re.IGNORECASE,
)
# Títulos da página que a coleta real colou no começo ou no fim do endereço. Só se cortam os
# vistos (e só inteiros, seguidos ou precedidos de vírgula); outro rótulo parecido não é cortado.
_ROTULOS_DO_COMECO = (
    r"Embassy of Brazil",
    r"Consulate[- ]General of Brazil(?: in [^,]+)?",
    r"Endere[çc]o da chancelaria",
    r"Address",
)
_ROTULOS_DO_FIM = (
    r"Jurisdi[çc][ãa]o",
    r"Endere[çc]o Postal",
    r"Postal Address",
    r"Emerg[êe]ncias Consulares",
)
_COMECA_COM_ROTULO = re.compile(rf"^(?:{'|'.join(_ROTULOS_DO_COMECO)})\s*,\s*", re.IGNORECASE)
_TERMINA_COM_ROTULO = re.compile(rf"\s*,\s*(?:{'|'.join(_ROTULOS_DO_FIM)})\s*$", re.IGNORECASE)
MAXIMO_DE_LINHAS_DO_ENDERECO = 8
MAXIMO_DE_LINHAS_NO_BLOCO = 5
MAXIMO_DE_LINHAS_ANTES_DO_NUMERO = 2
MAXIMO_DE_PALAVRAS_ANTES_DO_NUMERO = 6
MINIMO_DE_PALAVRAS_DA_PROSA = 7  # sem número e com tantas palavras: prosa, não endereço
MAXIMO_DE_PALAVRAS_DE_UMA_LINHA = 25  # linha mais longa que isso não é endereço (é um texto)
MINIMO_DE_PALAVRAS_DA_FRASE_COM_NUMERO = 10
MINIMO_DE_PALAVRAS_DA_FRASE = 4  # sem número, com ponto final e tantas palavras: uma frase
MINIMO_DE_CARACTERES_DO_ENDERECO = 10
MAXIMO_DE_CARACTERES_DO_ENDERECO = 300

_PLANTAO = re.compile(r"plant[ãa]o|plantonista", re.IGNORECASE)
_NUMERO_APOS_PLANTAO = re.compile(
    r"^(?P<meio>[^:.+()\d]{0,100}?)\s*:?\s*(?P<telefone>\(?\+?\d[\d\s().\-–]{6,}\d)"
)
_PLANTAO_DO_MINISTERIO = re.compile(r"minist[ée]rio|itamaraty|bras[ií]lia|\bmre\b", re.IGNORECASE)
MINIMO_DE_DIGITOS = 8
MAXIMO_DE_DIGITOS = 15  # limite do plano internacional de numeração (E.164)
_JANELA_APOS_PLANTAO = 160

# Páginas do posto onde vale procurar, da mais promissora para a menos
_PRIORIDADE_DOS_LINKS = (
    re.compile(r"emergenc"),
    re.compile(r"fale (com|conosco)|contato"),
    re.compile(r"assistencia a brasileiros|como chegar|endereco"),
)


@dataclass(frozen=True)
class ContatoExtraido:
    endereco: str | None
    telefone_plantao: str | None


def _corpo(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    return soup.select_one("#content-core") or soup


_TAGS_DE_BLOCO = (
    "p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "tr", "td", "th",
    "section", "article", "address", "table", "blockquote", "dl", "dt", "dd",
)  # fmt: skip


def _linhas(bloco: Tag | BeautifulSoup) -> list[str]:
    """Texto do bloco, uma linha por parágrafo, item ou `<br>`. Tags de texto (`<sup>`, `<b>`,
    `<a>`) não quebram a linha: "4<sup>º</sup> andar" continua sendo "4º andar"."""
    copia = BeautifulSoup(str(bloco), "html.parser")
    for quebra in copia.find_all("br"):
        quebra.replace_with("\n")
    for tag in copia.find_all(_TAGS_DE_BLOCO):
        tag.insert_before("\n")
        tag.insert_after("\n")
    texto = copia.get_text("").replace("\xa0", " ")
    linhas = (" ".join(linha.split()) for linha in texto.splitlines())
    return [linha for linha in linhas if linha]


def _juntar_endereco(linhas: list[str]) -> str:
    """Junta as linhas com vírgula, exceto observações entre parênteses, que seguem a anterior."""
    partes: list[str] = []
    for linha in linhas:
        if partes and linha.startswith("("):
            partes[-1] = f"{partes[-1]} {linha}"
        else:
            partes.append(linha)
    return ", ".join(partes)


def sem_rotulos_de_pagina(endereco: str) -> str:
    """Tira do começo e do fim do endereço os títulos da página que vieram colados nele."""
    anterior = None
    while anterior != endereco:
        anterior = endereco
        endereco = _TERMINA_COM_ROTULO.sub("", _COMECA_COM_ROTULO.sub("", endereco, count=1))
    return endereco.strip()


def _endereco_em_address(soup: BeautifulSoup) -> str | None:
    for bloco in soup.select("address"):
        endereco = sem_rotulos_de_pagina(
            _juntar_endereco([_aparar(linha) for linha in _linhas(bloco) if _tem_texto(linha)])
        )
        if _endereco_valido(endereco):
            return endereco
    return None


def _aparar(linha: str) -> str:
    """Sem a pontuação solta das pontas (":", "-", "/"), que sobra de rótulos partidos."""
    return linha.strip(" :;-–/|,")


def _tem_texto(linha: str) -> bool:
    return any(caractere.isalnum() for caractere in linha)


def _endereco_valido(endereco: str) -> bool:
    """Um endereço de verdade tem tamanho razoável e número (da rua ou do código postal), nunca
    e-mail nem link. Melhor deixar vazio do que mostrar um título ou rótulo como endereço."""
    if not MINIMO_DE_CARACTERES_DO_ENDERECO <= len(endereco) <= MAXIMO_DE_CARACTERES_DO_ENDERECO:
        return False
    if "@" in endereco or "http" in endereco.lower() or _NAO_E_ENDERECO.search(endereco):
        return False
    return any(c.isdigit() for c in endereco) or _SEM_NUMERO_DE_RUA.search(endereco) is not None


def _e_prosa(texto: str) -> bool:
    """Frase solta, não parte do endereço: texto longo, ou uma frase que termina em ponto. Sem
    número, o limite é bem menor (um endereço sem número é curto)."""
    palavras = len(texto.split())
    if palavras > MAXIMO_DE_PALAVRAS_DE_UMA_LINHA:
        return True
    if any(c.isdigit() for c in texto):
        return palavras >= MINIMO_DE_PALAVRAS_DA_FRASE_COM_NUMERO and texto.endswith(".")
    return palavras >= MINIMO_DE_PALAVRAS_DA_PROSA or (
        palavras >= MINIMO_DE_PALAVRAS_DA_FRASE and texto.endswith(".")
    )


def _coletar_bloco(linhas: list[str], bloco: list[str]) -> list[str]:
    """As linhas do endereço, a partir de `bloco` (já começado, no caso "Endereço: Rua A, 10").

    Sem começo, o endereço começa na primeira linha com número que não seja menu, aviso, frase ou o
    nome da representação; as linhas curtas e limpas logo antes dela entram junto ("Al-Harthia,
    Zaitoun Street" antes de "Quarter 213"). Depois de começar, segue até o próximo título, rótulo,
    menu ou frase.
    """
    pendentes: list[str] = []
    for linha in linhas[:MAXIMO_DE_LINHAS_DO_ENDERECO]:
        texto = _aparar(linha)
        if not _tem_texto(texto):
            continue  # linha só de pontuação (":") ou vazia
        com_rotulo = ":" in linha or "@" in texto
        if bloco:
            fim = _FIM_DO_ENDERECO.match(texto) or _NAO_E_ENDERECO.search(texto)
            if fim or com_rotulo or _e_prosa(texto):
                break
            bloco.append(texto)
            if len(bloco) >= MAXIMO_DE_LINHAS_NO_BLOCO:
                break
            continue
        if _FIM_DO_ENDERECO.match(texto):
            break  # o título era seguido de telefone, e-mail ou outro assunto: sem endereço
        if _NAO_E_ENDERECO.search(texto) or com_rotulo or _e_prosa(texto):
            pendentes.clear()
            continue
        if _NOME_DA_REPRESENTACAO.match(texto):
            continue
        if any(c.isdigit() for c in texto):
            bloco = [*pendentes[-MAXIMO_DE_LINHAS_ANTES_DO_NUMERO:], texto]
        elif len(texto.split()) <= MAXIMO_DE_PALAVRAS_ANTES_DO_NUMERO:
            pendentes.append(texto)
        else:
            pendentes.clear()
    return bloco


def _endereco_por_titulo(linhas: list[str]) -> str | None:
    for posicao, linha in enumerate(linhas):
        achado = _ROTULO_DO_ENDERECO.match(linha)
        if achado is None:
            continue
        resto = achado.group("resto").strip()
        if _ENDERECO_QUE_NAO_E_DE_RUA.match(resto):
            continue  # "Endereço eletrônico", "Endereço de e-mail"
        # "Endereço: Rua A, 10" já começa o endereço; "Endereço", "Endereço e contatos" e
        # "Endereço do Consulado" são títulos, e o endereço vem nas linhas seguintes
        inicio = [_aparar(resto)] if resto.startswith(":") and _tem_texto(resto) else []
        candidato = sem_rotulos_de_pagina(
            _juntar_endereco(_coletar_bloco(linhas[posicao + 1 :], inicio))
        )
        if _endereco_valido(candidato):
            return candidato
    return None


def _telefone_de_plantao(linhas: list[str]) -> str | None:
    texto = " ".join(linhas)
    for achado in _PLANTAO.finditer(texto):
        janela = texto[achado.end() : achado.end() + _JANELA_APOS_PLANTAO]
        numero = _NUMERO_APOS_PLANTAO.match(janela)
        if numero is None or _PLANTAO_DO_MINISTERIO.search(numero.group("meio")):
            continue
        telefone = " ".join(numero.group("telefone").split())
        if telefone.count("(") > telefone.count(")"):
            telefone = telefone[: telefone.rindex("(")].rstrip()  # "+964 780 (24 horas)"
        digitos = sum(caractere.isdigit() for caractere in telefone)
        if MINIMO_DE_DIGITOS <= digitos <= MAXIMO_DE_DIGITOS:
            return telefone
    return None


def extrair_contato(html: str) -> ContatoExtraido:
    """Endereço e telefone de plantão de uma página de posto; nulo no que não achar."""
    soup = BeautifulSoup(html, "html.parser")
    linhas = _linhas(_corpo(soup))
    return ContatoExtraido(
        endereco=_endereco_em_address(soup) or _endereco_por_titulo(linhas),
        telefone_plantao=_telefone_de_plantao(linhas),
    )


def _prioridade_do_link(texto: str, caminho: str) -> int | None:
    alvo = sem_acentos(f"{texto} {caminho.replace('-', ' ')}")
    for prioridade, padrao in enumerate(_PRIORIDADE_DOS_LINKS):
        if padrao.search(alvo):
            return prioridade
    return None


def links_de_contato(html: str, url_da_pagina: str, *, limite: int = 3) -> list[str]:
    """Subpáginas do próprio posto (emergências, fale conosco...) onde o contato costuma estar.

    Só entram links do mesmo host e abaixo do caminho do posto: os menus gerais do MRE
    ("Emergências no Exterior", "Fale conosco") são iguais em todos os postos e ficam de fora.
    """
    pagina = urlsplit(url_da_pagina)
    base = pagina.path.rstrip("/") + "/"
    soup = BeautifulSoup(html, "html.parser")
    achados: dict[str, int] = {}
    for link in soup.select("a[href]"):
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        destino = urlsplit(urljoin(url_da_pagina, href.strip()))
        if (destino.scheme, destino.netloc) != (pagina.scheme, pagina.netloc):
            continue
        if not destino.path.startswith(base) or destino.path.rstrip("/") + "/" == base:
            continue
        prioridade = _prioridade_do_link(link.get_text(" ", strip=True), destino.path)
        if prioridade is None:
            continue
        url = urlunsplit((destino.scheme, destino.netloc, destino.path, "", ""))
        achados[url] = min(prioridade, achados.get(url, prioridade))
    ordem = {url: posicao for posicao, url in enumerate(achados)}
    return sorted(achados, key=lambda url: (achados[url], ordem[url]))[:limite]
