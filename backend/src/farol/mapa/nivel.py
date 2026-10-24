"""Regra do nível de cada território (data-model.md, "Regra do nível"; FR-002, 007, 008, 031).

Função pura sobre linhas já carregadas: nenhuma consulta por país. A entrada traz só o que vale:
alertas confirmados por uma coleta completa e ainda na lista, cada um com a classificação do seu
hash confirmado (ou sem ela, se estiver pendente).

Em resumo, para cada território:
  - nunca houve coleta completa: "não verificado" (FR-002);
  - vale o alerta de viagem mais recente que o cita (a dependência também considera o do
    soberano); empate de datas: o nível mais grave (FR-007b);
  - o mais recente "normalizada": "sem alerta", sem regiões; só regional: "sem alerta" com região;
  - alerta pendente (sem classificação válida) cujo título cita o território: se for o mais
    recente, "não verificado" (FR-008). Na mesma data de um classificado, o pendente vence: na
    dúvida, o país nunca aparece como "sem alerta" (SC-003);
  - ninguém cita o território: "sem alerta".
"""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from farol.dominio import NivelAlerta


class NivelExibido(StrEnum):
    """Nível de um território no mapa (FR-001)."""

    SEM_ALERTA = "sem_alerta"
    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"
    NAO_VERIFICADO = "nao_verificado"


class NivelRegional(StrEnum):
    """Nível de uma região em destaque (a normalizada nunca aparece)."""

    EVITAR = "evitar"
    NAO_VIAJAR = "nao_viajar"


@dataclass(frozen=True)
class Regiao:
    nome: str
    nivel: NivelRegional


# ----------------------------------------------------------------------------- entrada
@dataclass(frozen=True)
class RegiaoDoAlerta:
    nome: str
    nivel: NivelAlerta


@dataclass(frozen=True)
class ItemDoAlerta:
    """O que um alerta classificado diz sobre um território."""

    territorio: str
    nivel_pais: NivelAlerta | None  # None = o alerta só vale para regiões do território
    regioes: tuple[RegiaoDoAlerta, ...] = ()


@dataclass(frozen=True)
class AlertaParaNivel:
    id: int
    titulo: str  # o título confirmado: identifica o país de um alerta pendente
    data_ref: datetime  # coalesce(modificado_em, publicado_em) da versão confirmada
    itens: tuple[ItemDoAlerta, ...] | None  # None = pendente; () = não é alerta de viagem


@dataclass(frozen=True)
class TerritorioParaNivel:
    codigo: str
    soberano: str | None
    nomes: tuple[str, ...]  # como o título de um alerta pode citar o território


# ----------------------------------------------------------------------------- saída
@dataclass(frozen=True)
class NivelDoTerritorio:
    nivel: NivelExibido
    regioes: tuple[Regiao, ...] = ()  # todas as regiões do alerta que rege (sem as normalizadas)
    regioes_em_destaque: tuple[Regiao, ...] = ()  # só as que merecem destaque no mapa (FR-004)
    so_regional: bool = False  # o alerta que rege só tem nível regional (FR-007)
    alerta_id: int | None = None  # o alerta que rege o nível


# ----------------------------------------------------------------------------- títulos
def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def titulo_cita(titulo: str, nomes: Iterable[str]) -> bool:
    """O título cita algum dos nomes (sem acento, sem diferença de maiúscula, palavra inteira)."""
    alvo = _normalizar(titulo)
    for nome in nomes:
        normalizado = _normalizar(nome)
        if not normalizado:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(normalizado)}(?![a-z0-9])", alvo):
            return True
    return False


# ----------------------------------------------------------------------------- cálculo
_GRAVIDADE = {NivelAlerta.NORMALIZADA: 1, NivelAlerta.EVITAR: 2, NivelAlerta.NAO_VIAJAR: 3}
_GRAVIDADE_PENDENTE = 4
_EXIBIDO = {
    NivelAlerta.EVITAR: NivelExibido.EVITAR,
    NivelAlerta.NAO_VIAJAR: NivelExibido.NAO_VIAJAR,
}
_REGIONAL = {
    NivelAlerta.EVITAR: NivelRegional.EVITAR,
    NivelAlerta.NAO_VIAJAR: NivelRegional.NAO_VIAJAR,
}


@dataclass(frozen=True)
class _Candidato:
    alerta: AlertaParaNivel
    item: ItemDoAlerta | None  # None = alerta pendente que cita o território pelo nome

    @property
    def chave(self) -> tuple[datetime, int]:
        if self.item is None:
            return self.alerta.data_ref, _GRAVIDADE_PENDENTE
        niveis = [r.nivel for r in self.item.regioes]
        if self.item.nivel_pais is not None:
            niveis.append(self.item.nivel_pais)
        return self.alerta.data_ref, max((_GRAVIDADE[n] for n in niveis), default=0)


def _regioes(item: ItemDoAlerta) -> tuple[Regiao, ...]:
    return tuple(Regiao(r.nome, _REGIONAL[r.nivel]) for r in item.regioes if r.nivel in _REGIONAL)


def _resultado(vencedor: _Candidato) -> NivelDoTerritorio:
    item = vencedor.item
    if item is None:
        return NivelDoTerritorio(NivelExibido.NAO_VERIFICADO, alerta_id=vencedor.alerta.id)
    if item.nivel_pais is NivelAlerta.NORMALIZADA:
        return NivelDoTerritorio(NivelExibido.SEM_ALERTA, alerta_id=vencedor.alerta.id)

    regioes = _regioes(item)
    if item.nivel_pais is None:
        return NivelDoTerritorio(
            NivelExibido.SEM_ALERTA,
            regioes=regioes,
            regioes_em_destaque=regioes,
            so_regional=bool(regioes),
            alerta_id=vencedor.alerta.id,
        )
    gravidade_do_pais = _GRAVIDADE[item.nivel_pais]
    destaque = tuple(
        r for r in regioes if _GRAVIDADE[NivelAlerta(r.nivel.value)] > gravidade_do_pais
    )
    return NivelDoTerritorio(
        _EXIBIDO[item.nivel_pais],
        regioes=regioes,
        regioes_em_destaque=destaque,
        alerta_id=vencedor.alerta.id,
    )


def calcular_niveis(
    territorios: Sequence[TerritorioParaNivel],
    alertas: Sequence[AlertaParaNivel],
    *,
    houve_coleta_completa: bool,
) -> dict[str, NivelDoTerritorio]:
    if not houve_coleta_completa:
        return {t.codigo: NivelDoTerritorio(NivelExibido.NAO_VERIFICADO) for t in territorios}

    itens_por_territorio: dict[str, list[_Candidato]] = {}
    pendentes: list[AlertaParaNivel] = []
    for alerta in alertas:
        if alerta.itens is None:
            pendentes.append(alerta)
            continue
        for item in alerta.itens:
            itens_por_territorio.setdefault(item.territorio, []).append(_Candidato(alerta, item))

    nomes_por_codigo = {t.codigo: t.nomes for t in territorios}
    resultado: dict[str, NivelDoTerritorio] = {}
    for territorio in territorios:
        # a dependência também considera o soberano (FR-031)
        codigos = [territorio.codigo]
        if territorio.soberano is not None:
            codigos.append(territorio.soberano)
        candidatos = [c for codigo in codigos for c in itens_por_territorio.get(codigo, [])]
        nomes = [n for codigo in codigos for n in nomes_por_codigo.get(codigo, ())]
        candidatos += [_Candidato(p, None) for p in pendentes if titulo_cita(p.titulo, nomes)]

        if not candidatos:
            resultado[territorio.codigo] = NivelDoTerritorio(NivelExibido.SEM_ALERTA)
        else:
            resultado[territorio.codigo] = _resultado(max(candidatos, key=lambda c: c.chave))
    return resultado
