"""Consolidação: das linhas da fonte a um candidato por território do mapa.

Várias linhas para o mesmo código (Santa Helena, Ascensão e Tristão da Cunha; a linha do Reino
Unido e das dependências da Coroa) são tratadas como partes de um rótulo combinado (FR-007): vale a
categoria mais exigente e "Outra situação" vence. O módulo é puro: não toca o banco nem a rede.
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.vistos.dicionario import (
    ClassificacaoDoRotulo,
    Dicionario,
    calcular_hash_observacao,
    mais_exigente,
)
from farol.vistos.fonte import TABELA_PRINCIPAL, LinhaDaFonte
from farol.vistos.permanencia import (
    SEM_PERMANENCIA,
    Permanencia,
    TipoDePermanencia,
    ler_permanencia,
)

SEPARADOR_DE_ROTULOS = " / "


@dataclass(frozen=True)
class Observacao:
    """A nota de uma linha da fonte; o hash do texto é a chave para não traduzir de novo."""

    texto: str
    hash: str


@dataclass(frozen=True)
class Candidato:
    """O que a leitura de hoje diz de um território, antes da regra de retenção."""

    codigo: str
    categoria: CategoriaDeVisto
    motivo_outra: MotivoOutraSituacao | None
    rotulo_original: str  # os rótulos das linhas, separados por " / "
    linhas_fonte: tuple[LinhaDaFonte, ...]  # na ordem da fonte
    hash_fonte: str  # muda só quando a fonte muda, nunca por causa do dicionário
    aceita_rg: bool
    varia_conforme_motivo: bool
    permanencia: Permanencia
    observacoes: tuple[Observacao, ...]
    hash_observacao: str | None  # só para os códigos de `regras_por_pais.yaml`


@dataclass(frozen=True)
class NomeDesconhecido:
    tabela: str
    nome: str  # como na fonte


@dataclass(frozen=True)
class RotuloDesconhecido:
    rotulo: str  # o rótulo inteiro da linha, em chave de consulta
    tabela: str
    nome: str  # o país onde apareceu, como na fonte


@dataclass(frozen=True)
class Consolidacao:
    candidatos: dict[str, Candidato]  # por código do mapa, na ordem em que aparecem na fonte
    nomes_desconhecidos: tuple[NomeDesconhecido, ...]
    rotulos_desconhecidos: tuple[RotuloDesconhecido, ...]
    ignoradas: tuple[LinhaDaFonte, ...]  # linhas de nomes ignorados de propósito

    @property
    def paises_reconhecidos(self) -> int:
        """Códigos distintos do mapa ligados a alguma linha, sem contar os ignorados (FR-010)."""
        return len(self.candidatos)


def calcular_hash_da_fonte(linhas: Iterable[LinhaDaFonte]) -> str:
    """SHA-256 do JSON canônico das linhas (ordenadas), sem olhar para o dicionário."""
    ordenadas = sorted(
        (linha.como_dicionario() for linha in linhas),
        key=lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True),
    )
    canonico = json.dumps(ordenadas, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _permanencia(linhas: Sequence[LinhaDaFonte]) -> Permanencia:
    """Só a coluna "Allowed stay" da tabela principal vale (O3); linha sem prazo não diverge."""
    prazos = {
        lida
        for linha in linhas
        if linha.tabela == TABELA_PRINCIPAL
        and (lida := ler_permanencia(linha.permanencia)).tipo is not TipoDePermanencia.NENHUMA
    }
    if not prazos:
        return SEM_PERMANENCIA
    if len(prazos) > 1:
        return Permanencia(TipoDePermanencia.PRAZOS_DIVERGENTES, None)
    return next(iter(prazos))


def _observacoes(linhas: Sequence[LinhaDaFonte]) -> tuple[Observacao, ...]:
    return tuple(
        Observacao(linha.notas, hashlib.sha256(linha.notas.encode("utf-8")).hexdigest())
        for linha in linhas
        if linha.notas
    )


def _categoria(
    resultados: Sequence[ClassificacaoDoRotulo],
) -> tuple[CategoriaDeVisto, MotivoOutraSituacao | None]:
    """Mais exigente das linhas; "Outra situação" vence, e o desconhecido vence o conhecido."""
    if any(r.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO for r in resultados):
        return CategoriaDeVisto.OUTRA_SITUACAO, MotivoOutraSituacao.ROTULO_DESCONHECIDO
    if any(r.categoria is CategoriaDeVisto.OUTRA_SITUACAO for r in resultados):
        return CategoriaDeVisto.OUTRA_SITUACAO, MotivoOutraSituacao.ROTULO_CONHECIDO
    return mais_exigente(r.categoria for r in resultados), None


def _montar_candidato(
    codigo: str, linhas: Sequence[LinhaDaFonte], dicionario: Dicionario
) -> tuple[Candidato, list[RotuloDesconhecido]]:
    resultados = [dicionario.classificar_rotulo(linha.rotulo, linha.notas) for linha in linhas]
    categoria, motivo = _categoria(resultados)
    desconhecidos = [
        RotuloDesconhecido(resultado.rotulo_para_revisao, linha.tabela, linha.nome)
        for linha, resultado in zip(linhas, resultados, strict=True)
        if resultado.rotulo_para_revisao is not None
    ]
    regra = dicionario.regras.get(codigo)
    permanencia = _permanencia(linhas)
    if regra is not None and regra.prazos_diferem_por_motivo:
        permanencia = Permanencia(TipoDePermanencia.VARIA_CONFORME_MOTIVO, None)
    candidato = Candidato(
        codigo=codigo,
        categoria=categoria,
        motivo_outra=motivo,
        rotulo_original=SEPARADOR_DE_ROTULOS.join(linha.rotulo for linha in linhas),
        linhas_fonte=tuple(linhas),
        hash_fonte=calcular_hash_da_fonte(linhas),
        # o RG é afirmado só por uma linha isolada com o rótulo e a frase "ID card"
        aceita_rg=len(linhas) == 1 and resultados[0].aceita_rg,
        varia_conforme_motivo=regra is not None and regra.varia_conforme_motivo,
        permanencia=permanencia,
        observacoes=_observacoes(linhas),
        hash_observacao=(
            calcular_hash_observacao(linha.notas for linha in linhas) if regra is not None else None
        ),
    )
    return candidato, desconhecidos


def consolidar(linhas: Iterable[LinhaDaFonte], dicionario: Dicionario) -> Consolidacao:
    """Liga cada linha a um código, agrupa as linhas do mesmo código e lê rótulos e prazos.

    Nome ignorado de propósito não gera candidato. Nome desconhecido também não, e é devolvido
    para revisão; o rótulo de uma linha cujo nome não liga a nenhum país não é registrado (não há
    país onde ele tenha aparecido).
    """
    por_codigo: dict[str, list[LinhaDaFonte]] = {}
    nomes_desconhecidos: list[NomeDesconhecido] = []
    ignoradas: list[LinhaDaFonte] = []
    for linha in linhas:
        ligacao = dicionario.ligar_nome(linha.nome)
        if ligacao.codigo is not None:
            por_codigo.setdefault(ligacao.codigo, []).append(linha)
        elif ligacao.ignorado:
            ignoradas.append(linha)
        else:
            nomes_desconhecidos.append(NomeDesconhecido(linha.tabela, linha.nome))

    candidatos: dict[str, Candidato] = {}
    rotulos_desconhecidos: list[RotuloDesconhecido] = []
    for codigo, do_codigo in por_codigo.items():
        candidato, desconhecidos = _montar_candidato(codigo, do_codigo, dicionario)
        candidatos[codigo] = candidato
        rotulos_desconhecidos.extend(desconhecidos)
    return Consolidacao(
        candidatos=candidatos,
        nomes_desconhecidos=tuple(nomes_desconhecidos),
        rotulos_desconhecidos=tuple(rotulos_desconhecidos),
        ignoradas=tuple(ignoradas),
    )
