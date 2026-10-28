"""Dicionários de leitura da fonte: rótulos, nomes e regras por país.

Os três arquivos YAML ficam em `dicionarios_yaml/`, dentro do pacote (para irem na imagem do Docker
e serem testados com o código), e são lidos por `importlib.resources`. O formato e as regras de
leitura estão em `specs/002-visto-brasileiros/contracts/dicionario-de-rotulos.md`.

Erro de formato levanta `ErroDeDicionario`: quem derruba é o teste, não a coleta em produção.
"""

import hashlib
import re
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

import yaml

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.infra import obter_logger
from farol.vistos.normalizacao import chave_de_consulta, chave_de_rotulo, normalizar

DIRETORIO_DOS_DICIONARIOS: Traversable = files("farol.vistos").joinpath("dicionarios_yaml")

ARQUIVO_DE_ROTULOS = "rotulos.yaml"
ARQUIVO_DE_NOMES = "nomes.yaml"
ARQUIVO_DE_REGRAS = "regras_por_pais.yaml"

# Da menos para a mais exigente (FR-007); "Outra situação" fica fora da ordem.
ORDEM_DE_EXIGENCIA: tuple[CategoriaDeVisto, ...] = (
    CategoriaDeVisto.ISENTO,
    CategoriaDeVisto.VISTO_NA_CHEGADA,
    CategoriaDeVisto.AUTORIZACAO_ELETRONICA,
    CategoriaDeVisto.VISTO_EXIGIDO,
)

_SEPARADOR_DE_PARTES = " / "
_FRASE_DO_RG = "id card"
_CAMPOS_DE_ROTULO = {"categoria", "aceita_rg", "exemplo", "motivo"}
_CAMPOS_DE_REGRA = {"varia_conforme_motivo", "prazos_diferem_por_motivo", "hash_observacao"}
_HASH = re.compile(r"[0-9a-f]{64}")

_log = obter_logger("farol.vistos")


class ErroDeDicionario(Exception):
    """Um dos arquivos de dicionário está mal formado."""


def mais_exigente(categorias: Iterable[CategoriaDeVisto]) -> CategoriaDeVisto:
    """A categoria mais exigente da ordem do FR-007. Não aceita "Outra situação" nem lista vazia."""
    lista = list(categorias)
    if not lista or any(c not in ORDEM_DE_EXIGENCIA for c in lista):
        raise ValueError("só as quatro categorias da ordem de exigência têm um 'mais exigente'")
    return max(lista, key=ORDEM_DE_EXIGENCIA.index)


@dataclass(frozen=True)
class EntradaDeRotulo:
    categoria: CategoriaDeVisto
    aceita_rg: bool = False
    exemplo: str | None = None
    motivo: str | None = None


@dataclass(frozen=True)
class RegraDoPais:
    varia_conforme_motivo: bool
    prazos_diferem_por_motivo: bool
    hash_observacao: str


@dataclass(frozen=True)
class ClassificacaoDoRotulo:
    """Resultado de ler o rótulo de uma linha da fonte."""

    categoria: CategoriaDeVisto
    motivo_outra: MotivoOutraSituacao | None  # só quando a categoria é "Outra situação"
    aceita_rg: bool
    rotulo_para_revisao: str | None  # o rótulo inteiro (chave), se alguma parte é desconhecida


@dataclass(frozen=True)
class LigacaoDoNome:
    codigo: str | None
    ignorado: bool
    motivo: str | None  # o motivo de ignorar

    @property
    def desconhecido(self) -> bool:
        return self.codigo is None and not self.ignorado


@dataclass(frozen=True)
class Dicionario:
    rotulos: Mapping[str, EntradaDeRotulo]  # chave de consulta -> entrada
    nomes: Mapping[str, str]  # nome (chave de consulta) -> código do mapa
    ignorar: Mapping[str, str]  # nome (chave de consulta) -> motivo
    regras: Mapping[str, RegraDoPais]  # código -> regra

    # ------------------------------------------------------------------ rótulos
    def classificar_rotulo(self, rotulo: str, notas: str = "") -> ClassificacaoDoRotulo:
        """Regras 1 a 4 do contrato: direto, combinado (mais exigente), outra situação."""
        chave = chave_de_rotulo(rotulo)
        entrada = self.rotulos.get(chave)
        if entrada is not None:  # regra 1
            return self._de_uma_entrada(entrada, chave, notas)

        partes = chave.split(_SEPARADOR_DE_PARTES)
        entradas = [self.rotulos.get(parte.strip()) for parte in partes]
        if len(partes) > 1 and all(e is not None for e in entradas):  # regra 2
            categorias = [e.categoria for e in entradas if e is not None]
            if CategoriaDeVisto.OUTRA_SITUACAO in categorias:
                return ClassificacaoDoRotulo(
                    CategoriaDeVisto.OUTRA_SITUACAO,
                    MotivoOutraSituacao.ROTULO_CONHECIDO,
                    False,
                    None,
                )
            return ClassificacaoDoRotulo(mais_exigente(categorias), None, False, None)

        # regra 3: alguma parte desconhecida (ou rótulo vazio)
        return ClassificacaoDoRotulo(
            CategoriaDeVisto.OUTRA_SITUACAO,
            MotivoOutraSituacao.ROTULO_DESCONHECIDO,
            False,
            chave or None,
        )

    def _de_uma_entrada(
        self, entrada: EntradaDeRotulo, chave: str, notas: str
    ) -> ClassificacaoDoRotulo:
        aceita_rg = False
        if entrada.aceita_rg:  # regra 4: o rótulo e a frase "ID card" na nota
            aceita_rg = _FRASE_DO_RG in normalizar(notas).casefold()
            if not aceita_rg:
                _log.warning(
                    "vistos: rótulo %r aceita RG, mas a nota não traz a frase 'ID card'; "
                    "o RG não foi afirmado",
                    chave,
                )
        if entrada.categoria is CategoriaDeVisto.OUTRA_SITUACAO:
            return ClassificacaoDoRotulo(
                entrada.categoria, MotivoOutraSituacao.ROTULO_CONHECIDO, aceita_rg, None
            )
        return ClassificacaoDoRotulo(entrada.categoria, None, aceita_rg, None)

    # ------------------------------------------------------------------ nomes
    def ligar_nome(self, nome: str) -> LigacaoDoNome:
        """O código do mapa do nome da fonte, ou o motivo de ignorá-lo, ou "desconhecido"."""
        chave = chave_de_consulta(nome)
        if chave in self.nomes:
            return LigacaoDoNome(self.nomes[chave], False, None)
        if chave in self.ignorar:
            return LigacaoDoNome(None, True, self.ignorar[chave])
        return LigacaoDoNome(None, False, None)


def calcular_hash_observacao(notas: Iterable[str]) -> str:
    """SHA-256 (UTF-8, hexadecimal) das notas normalizadas, na ordem da fonte, unidas por `\\n`.

    Notas em branco não entram: uma linha sem nota não tem observação.
    """
    textos = [normalizar(nota) for nota in notas]
    conteudo = "\n".join(texto for texto in textos if texto)
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- carregamento
def _ler_mapa(diretorio: Traversable, arquivo: str) -> dict[Any, Any]:
    caminho = diretorio.joinpath(arquivo)
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as erro:
        raise ErroDeDicionario(f"{arquivo}: arquivo não encontrado ({erro})") from erro
    try:
        conteudo = yaml.safe_load(texto)
    except yaml.YAMLError as erro:
        raise ErroDeDicionario(f"{arquivo}: YAML inválido ({erro})") from erro
    if not isinstance(conteudo, dict):
        raise ErroDeDicionario(f"{arquivo}: deveria ser um mapa YAML")
    return conteudo


def _chave(valor: object, arquivo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroDeDicionario(f"{arquivo}: chave {valor!r} deveria ser um texto não vazio")
    return valor


def _booleano(valor: object, onde: str) -> bool:
    if not isinstance(valor, bool):
        raise ErroDeDicionario(f"{onde}: deveria ser verdadeiro ou falso, veio {valor!r}")
    return valor


def _texto_opcional(valor: object, onde: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErroDeDicionario(f"{onde}: deveria ser um texto, veio {valor!r}")
    return valor


def _carregar_rotulos(diretorio: Traversable) -> dict[str, EntradaDeRotulo]:
    rotulos: dict[str, EntradaDeRotulo] = {}
    for bruto, entrada in _ler_mapa(diretorio, ARQUIVO_DE_ROTULOS).items():
        nome = _chave(bruto, ARQUIVO_DE_ROTULOS)
        onde = f"{ARQUIVO_DE_ROTULOS}, rótulo {nome!r}"
        if not isinstance(entrada, dict):
            raise ErroDeDicionario(f"{onde}: deveria ser um mapa com a categoria")
        desconhecidos = set(entrada) - _CAMPOS_DE_ROTULO
        if desconhecidos:
            raise ErroDeDicionario(f"{onde}: campo(s) desconhecido(s) {sorted(desconhecidos)}")
        bruta = entrada.get("categoria")
        try:
            categoria = CategoriaDeVisto(str(bruta))
        except ValueError as erro:
            valores = [c.value for c in CategoriaDeVisto]
            raise ErroDeDicionario(
                f"{onde}: categoria {bruta!r} inválida (use {valores})"
            ) from erro
        chave = chave_de_rotulo(nome)
        if chave in rotulos:
            raise ErroDeDicionario(f"{onde}: rótulo repetido depois de normalizar ({chave!r})")
        rotulos[chave] = EntradaDeRotulo(
            categoria=categoria,
            aceita_rg=_booleano(entrada.get("aceita_rg", False), f"{onde}, aceita_rg"),
            exemplo=_texto_opcional(entrada.get("exemplo"), f"{onde}, exemplo"),
            motivo=_texto_opcional(entrada.get("motivo"), f"{onde}, motivo"),
        )
    return rotulos


def _codigo(valor: object, onde: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ErroDeDicionario(
            f"{onde}: o código deveria ser um texto (entre aspas), veio {valor!r}; "
            "atenção: o YAML lê NO como falso"
        )
    return valor.strip()


def _carregar_nomes(
    diretorio: Traversable,
    codigos_validos: Collection[str] | None,
    codigos_neutros: Collection[str],
) -> tuple[dict[str, str], dict[str, str]]:
    conteudo = _ler_mapa(diretorio, ARQUIVO_DE_NOMES)
    desconhecidos = set(conteudo) - {"nomes", "ignorar"}
    if desconhecidos:
        raise ErroDeDicionario(
            f"{ARQUIVO_DE_NOMES}: seção(ões) desconhecida(s) {sorted(desconhecidos)}"
        )

    nomes: dict[str, str] = {}
    for bruto, valor in (conteudo.get("nomes") or {}).items():
        nome = _chave(bruto, ARQUIVO_DE_NOMES)
        onde = f"{ARQUIVO_DE_NOMES}, nome {nome!r}"
        codigo = _codigo(valor, onde)
        if codigos_validos is not None and codigo not in codigos_validos:
            raise ErroDeDicionario(f"{onde}: o código {codigo!r} não existe no mapa")
        if codigo in codigos_neutros:
            raise ErroDeDicionario(f"{onde}: o código {codigo!r} é de uma área neutra")
        chave = chave_de_consulta(nome)
        if chave in nomes:
            raise ErroDeDicionario(f"{onde}: nome repetido depois de normalizar ({chave!r})")
        nomes[chave] = codigo

    ignorar: dict[str, str] = {}
    for bruto, motivo in (conteudo.get("ignorar") or {}).items():
        nome = _chave(bruto, ARQUIVO_DE_NOMES)
        onde = f"{ARQUIVO_DE_NOMES}, ignorar {nome!r}"
        if not isinstance(motivo, str) or not motivo.strip():
            raise ErroDeDicionario(f"{onde}: todo nome ignorado precisa de um motivo")
        chave = chave_de_consulta(nome)
        if chave in ignorar:
            raise ErroDeDicionario(f"{onde}: nome repetido depois de normalizar ({chave!r})")
        if chave in nomes:
            raise ErroDeDicionario(f"{onde}: o nome {nome!r} está em 'nomes' e em 'ignorar'")
        ignorar[chave] = motivo.strip()
    return nomes, ignorar


def _carregar_regras(
    diretorio: Traversable,
    codigos_validos: Collection[str] | None,
    codigos_neutros: Collection[str],
) -> dict[str, RegraDoPais]:
    regras: dict[str, RegraDoPais] = {}
    for bruto, regra in _ler_mapa(diretorio, ARQUIVO_DE_REGRAS).items():
        codigo = _codigo(bruto, f"{ARQUIVO_DE_REGRAS}")
        onde = f"{ARQUIVO_DE_REGRAS}, país {codigo}"
        if codigos_validos is not None and codigo not in codigos_validos:
            raise ErroDeDicionario(f"{onde}: o código não existe no mapa")
        if codigo in codigos_neutros:
            raise ErroDeDicionario(f"{onde}: o código é de uma área neutra")
        if not isinstance(regra, dict) or set(regra) != _CAMPOS_DE_REGRA:
            raise ErroDeDicionario(
                f"{onde}: deveria ter exatamente os campos {sorted(_CAMPOS_DE_REGRA)}"
            )
        hash_observacao = regra["hash_observacao"]
        if not isinstance(hash_observacao, str) or not _HASH.fullmatch(hash_observacao):
            raise ErroDeDicionario(f"{onde}: hash_observacao deveria ter 64 dígitos hexadecimais")
        regras[codigo] = RegraDoPais(
            varia_conforme_motivo=_booleano(
                regra["varia_conforme_motivo"], f"{onde}, varia_conforme_motivo"
            ),
            prazos_diferem_por_motivo=_booleano(
                regra["prazos_diferem_por_motivo"], f"{onde}, prazos_diferem_por_motivo"
            ),
            hash_observacao=hash_observacao,
        )
    return regras


def carregar_dicionario(
    diretorio: Traversable = DIRETORIO_DOS_DICIONARIOS,
    *,
    codigos_validos: Collection[str] | None = None,
    codigos_neutros: Collection[str] = (),
) -> Dicionario:
    """Lê e valida os três arquivos.

    `codigos_validos` (os códigos de `territorio`) e `codigos_neutros` (as áreas neutras) só são
    conferidos se informados: o teste confere o conteúdo real contra o seed.
    """
    nomes, ignorar = _carregar_nomes(diretorio, codigos_validos, codigos_neutros)
    return Dicionario(
        rotulos=_carregar_rotulos(diretorio),
        nomes=nomes,
        ignorar=ignorar,
        regras=_carregar_regras(diretorio, codigos_validos, codigos_neutros),
    )


@cache
def dicionario_padrao() -> Dicionario:
    """Os dicionários do pacote, lidos uma vez por execução."""
    return carregar_dicionario()
