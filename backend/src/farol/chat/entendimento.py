"""Entendimento da pergunta pelo código (research D3). Funções puras, sem modelo.

Países: os nomes que a busca do site usa (`nome` e `rotulo_busca` sem o "(soberano)", e
`termos_busca`) mais `apelidos.yaml`, por palavra inteira e do nome mais longo para o mais curto;
um trecho já casado não casa de novo. Assunto: por palavras, com "fora do assunto" vencendo. O que
sobra (nem país, nem assunto, nem conectivo) decide se o código entendeu ou se o modelo é chamado.
País logo depois de uma palavra desconhecida ("Novo México") é parte de outro nome: não vale.
"""

import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from farol.chat.portas import TerritorioLido, TipoDeResposta

APELIDOS = Path(__file__).with_name("apelidos.yaml")
CODIGO_DO_BRASIL = "BR"


class Assunto(StrEnum):
    ALERTA = "alerta"
    VISTO = "visto"
    ALERTA_E_VISTO = "alerta_e_visto"
    FORA_DO_ASSUNTO = "fora_do_assunto"


# Palavras e expressões já normalizadas. "Fora do assunto" vence as outras.
FORA_DO_ASSUNTO = frozenset(
    {
        "embaixada", "embaixadas", "consulado", "consulados", "posto", "postos", "capital",
        "moeda", "idioma", "lingua", "clima", "recomenda", "recomendacoes", "quais paises",
        "lista", "telefone", "endereco", "seguro viagem", "seguro de viagem",
    }
)  # fmt: skip
ALERTA = frozenset(
    {
        "alerta", "alertas", "seguro", "segura", "seguranca", "perigo", "perigoso", "perigosa",
        "risco", "guerra", "conflito",
    }
)  # fmt: skip
# Só contam como alerta quando a pergunta não fala de visto ("visto para viajar ao Japão")
ALERTA_FRACO = frozenset({"viajar", "viagem"})
VISTO = frozenset(
    {
        "visto", "vistos", "visa", "passaporte", "rg", "identidade", "documento", "documentos",
        "entrar", "entrada", "permanencia",
    }
)  # fmt: skip
# Conectivos e verbos que não mudam o sentido: "e o Peru?", "me fala do Peru". Os de viagem também
# dizem que o país logo depois é mesmo o país: "quero conhecer Tailândia", "lua de mel Tailândia"
CONECTIVOS = frozenset(
    {
        "e", "o", "a", "os", "as", "ao", "aos", "um", "uma", "de", "do", "da", "dos", "das",
        "para", "pra", "pro", "no", "na", "nos", "nas", "em", "com", "por", "sobre", "me", "eu",
        "fala", "fale", "falar", "conta", "diz", "diga", "como", "esta", "estao", "ta", "que",
        "qual", "quanto", "tem", "ha", "voce", "pode", "poderia", "saber", "quero", "queria",
        "gostaria", "preciso", "precisa", "precisam", "posso", "ir", "vou", "indo", "saindo",
        "partindo", "situacao", "agora", "hoje", "atual", "oi", "ola", "favor", "brasileiro",
        "brasileiros", "brasileira", "brasileiras", "info", "informacao", "informacoes",
        "conhecer", "conhecendo", "conheci", "conheco", "visitar", "visitando", "visitei", "visito",
        "fui", "vai", "vamos", "irei", "viajando", "viajei", "viajo", "viajarei", "passar",
        "passando", "passei", "passo", "morar", "morando", "morei", "moro", "ferias", "lua", "mel",
    }
)  # fmt: skip
EXPRESSOES = {
    **dict.fromkeys(FORA_DO_ASSUNTO, Assunto.FORA_DO_ASSUNTO),
    **dict.fromkeys(ALERTA | ALERTA_FRACO, Assunto.ALERTA),
    **dict.fromkeys(VISTO, Assunto.VISTO),
}
MAIOR_EXPRESSAO = max(len(expressao.split()) for expressao in EXPRESSOES)
_PARENTESES = re.compile(r"\s*\([^)]*\)\s*$")


def normalizar(texto: str) -> str:
    """Sem acento, minúsculas, pontuação vira espaço (como `normalizar` da busca do site)."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(re.sub(r"[^\w]+", " ", sem_acento.lower()).split())


# ----------------------------------------------------------------------------- vocabulário
@dataclass(frozen=True)
class PaisCitado:
    nome: str  # o nome do site; no ambíguo, o termo do apelidos.yaml
    codigos: tuple[str, ...]  # mais de um = ambíguo
    opcoes: tuple[str, ...] = ()  # o que mostrar na pergunta de volta, se os nomes não distinguem

    @property
    def ambiguo(self) -> bool:
        return len(self.codigos) > 1


@dataclass(frozen=True)
class Apelidos:
    apelidos: Mapping[str, str]  # termo normalizado -> código
    ambiguos: Mapping[str, tuple[str, ...]]  # nome mostrado -> códigos
    opcoes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # nome -> opções


@cache
def _ler_yaml(caminho: Path) -> dict[str, Any]:
    conteudo: dict[str, Any] = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}
    return conteudo


def carregar_apelidos(codigos: Collection[str], caminho: Path = APELIDOS) -> Apelidos:
    """Lê o YAML e confere cada código contra os territórios (`ValueError` se algum faltar)."""
    dados = _ler_yaml(caminho)
    apelidos = {normalizar(str(t)): str(c) for t, c in (dados.get("apelidos") or {}).items()}
    ambiguos = {str(t): tuple(map(str, cs)) for t, cs in (dados.get("ambiguos") or {}).items()}
    for termo, codigos_do_termo in [(t, (c,)) for t, c in apelidos.items()] + list(
        ambiguos.items()
    ):
        for codigo in codigos_do_termo:
            if codigo not in codigos:
                raise ValueError(f"{caminho.name}: código {codigo!r} desconhecido em {termo!r}")
    opcoes = {
        str(t): tuple(map(str, os)) for t, os in (dados.get("opcoes_dos_ambiguos") or {}).items()
    }
    return Apelidos(apelidos, ambiguos, opcoes)


@dataclass(frozen=True)
class Vocabulario:
    termos: Mapping[str, PaisCitado]  # termo normalizado -> país (ou ambíguo)
    nomes: Mapping[str, str]  # código -> nome que distingue o território
    maior: int = field(default=1)  # palavras do termo mais longo


def montar_vocabulario(territorios: Sequence[TerritorioLido], apelidos: Apelidos) -> Vocabulario:
    # Kosovo e Malvinas têm o `nome` do soberano: dois "Argentina" não se distinguem
    nomes = {t.codigo: t.rotulo_busca if t.identidade_do_soberano else t.nome for t in territorios}
    codigos_por_termo: dict[str, list[str]] = {}

    def acrescentar(termo: str, codigo: str) -> None:
        lista = codigos_por_termo.setdefault(normalizar(termo), [])
        if codigo not in lista:
            lista.append(codigo)

    for t in territorios:
        # Kosovo e Malvinas têm o `nome` do soberano: "Sérvia" é a Sérvia, não o Kosovo
        if not t.identidade_do_soberano:
            acrescentar(_PARENTESES.sub("", t.nome), t.codigo)
        acrescentar(_PARENTESES.sub("", t.rotulo_busca), t.codigo)
        for termo in t.termos_busca:
            acrescentar(termo, t.codigo)
    for termo, codigo in apelidos.apelidos.items():
        acrescentar(termo, codigo)

    termos = {
        termo: PaisCitado(
            nomes[cs[0]] if len(cs) == 1 else _PARENTESES.sub("", nomes[cs[0]]), tuple(cs)
        )
        for termo, cs in codigos_por_termo.items()
        if termo
    }
    for nome, cs in apelidos.ambiguos.items():
        termos[normalizar(nome)] = PaisCitado(nome, cs, apelidos.opcoes.get(nome, ()))
    return Vocabulario(termos, nomes, max(len(t.split()) for t in termos) if termos else 1)


# ----------------------------------------------------------------------------- entendimento
@dataclass(frozen=True)
class Entendimento:
    paises: tuple[PaisCitado, ...]  # sem o Brasil, na ordem da pergunta
    brasil: bool
    assunto: Assunto | None
    sobra: bool  # há palavras que não são país, assunto nem conectivo

    @property
    def entendeu(self) -> bool:
        """O código responde sem o modelo (D3, passo 6)."""
        if self.assunto is Assunto.FORA_DO_ASSUNTO:
            return True
        if self.paises or self.brasil:
            return self.assunto is not None or not self.sobra
        return self.assunto is not None and not self.sobra  # "e o visto?" -> pedir o país


def _casar(
    palavras: list[str], usadas: list[bool], termos: Mapping[str, Any], maior: int
) -> list[tuple[int, Any]]:
    """Casa os termos por palavra inteira, do mais longo ao mais curto, sem reusar palavras."""
    casados: list[tuple[int, Any]] = []
    for tamanho in range(min(maior, len(palavras)), 0, -1):
        for inicio in range(len(palavras) - tamanho + 1):
            fim = inicio + tamanho
            if any(usadas[inicio:fim]):
                continue
            achado = termos.get(" ".join(palavras[inicio:fim]))
            if achado is not None:
                usadas[inicio:fim] = [True] * tamanho
                casados.append((inicio, achado))
    return sorted(casados, key=lambda par: par[0])


def entender(pergunta: str, vocabulario: Vocabulario) -> Entendimento:
    palavras = normalizar(pergunta).split()
    usadas = [False] * len(palavras)

    casados = _casar(palavras, usadas, vocabulario.termos, vocabulario.maior)
    expressoes = _casar(palavras, usadas, EXPRESSOES, MAIOR_EXPRESSAO)

    # shortcut: olha só a palavra de antes ("Novo México"). A de depois daria alarme falso em
    # "visto Japão amanhã"; nomes como "Irlanda do Norte" entram por apelidos.yaml.
    def _dentro_de_outro_nome(inicio: int) -> bool:
        return inicio > 0 and not usadas[inicio - 1] and palavras[inicio - 1] not in CONECTIVOS

    paises: list[PaisCitado] = []
    brasil = False
    if not any(_dentro_de_outro_nome(inicio) for inicio, _ in casados):
        for _, pais in casados:
            if pais.codigos == (CODIGO_DO_BRASIL,):
                brasil = True
            elif pais.codigos not in [p.codigos for p in paises]:
                paises.append(pais)

    achados = {assunto for _, assunto in expressoes}
    visto = Assunto.VISTO in achados
    alerta = any(
        palavras[i] not in ALERTA_FRACO or not visto
        for i, assunto in expressoes
        if assunto is Assunto.ALERTA
    )
    if Assunto.FORA_DO_ASSUNTO in achados:
        assunto: Assunto | None = Assunto.FORA_DO_ASSUNTO
    elif alerta and visto:
        assunto = Assunto.ALERTA_E_VISTO
    elif alerta:
        assunto = Assunto.ALERTA
    elif visto:
        assunto = Assunto.VISTO
    else:
        assunto = None

    sobra = any(
        not usada and palavra not in CONECTIVOS
        for palavra, usada in zip(palavras, usadas, strict=True)
    )
    return Entendimento(tuple(paises), brasil, assunto, sobra)


def decidir(entendimento: Entendimento) -> tuple[TipoDeResposta, PaisCitado | None]:
    """O tipo da resposta e o país respondido (só nos tipos com um país)."""
    paises = entendimento.paises
    if entendimento.assunto is Assunto.FORA_DO_ASSUNTO:
        return TipoDeResposta.FORA_DO_ASSUNTO, None
    if len(paises) > 1:
        return TipoDeResposta.UM_PAIS_POR_VEZ, None
    if paises:
        if paises[0].ambiguo:
            return TipoDeResposta.QUAL_DOS_PAISES, paises[0]
        tipo = {
            Assunto.ALERTA: TipoDeResposta.ALERTA,
            Assunto.VISTO: TipoDeResposta.VISTO,
        }.get(entendimento.assunto or Assunto.ALERTA_E_VISTO, TipoDeResposta.ALERTA_E_VISTO)
        return tipo, paises[0]
    if entendimento.brasil:
        return TipoDeResposta.BRASIL, None
    return TipoDeResposta.PEDIR_PAIS, None
