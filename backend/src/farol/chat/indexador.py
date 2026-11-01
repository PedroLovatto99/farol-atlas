"""Mantém o índice de trechos em dia com os alertas (contracts/indexacao-e-comandos.md).

`indexar_pendentes` compara, alerta por alerta, o índice com o que o alerta é hoje e corrige o que
estiver diferente, vetorizando só o que mudou: é idempotente e não toca nada que já está em dia.
`reindexar` é o comando da troca de modelo ou de dimensão. Nenhuma das duas faz `commit`: quem abre
a sessão (`abrir_sessao`) confirma. Cada alerta é gravado num SAVEPOINT próprio, e a vetorização
vem antes da escrita, então uma falha de rede ou de cota num alerta nunca estraga os trechos bons
dele nem atrapalha os outros.

O chat não importa o `mapa`: o `vigor` (alerta -> territórios cujo nível ele rege) chega pronto,
e os países que um aviso geral cita vêm de `citados` (texto -> códigos), também de fora. O aviso
geral é o alerta cuja classificação não define nível nenhum (fraude, aliciamento, saúde pública):
os países dele no índice são os que ele cita; os de um alerta de nível são os da classificação.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy.orm import Session

from farol.chat.fatiamento import fatiar
from farol.chat.protocolos import Embeddador
from farol.dominio import (
    AlertaElegivel,
    NovoTrecho,
    TrechoAlertaRepositorio,
    TrechoGravado,
)
from farol.infra import Relogio, RelogioDoSistema, obter_logger

_log = obter_logger("farol.chat")

Vigor = Mapping[int, frozenset[str]]
Citados = Callable[[str], Iterable[str]]
# (posição, total, id do alerta, "refeito" | "completo" | "falhou"), a cada alerta do `reindexar`
Andamento = Callable[[int, int, int, str], None]


class ErroDeEmbedding(RuntimeError):
    """O serviço de embeddings devolveu algo que o índice não aceita (quantidade ou tamanho)."""


@dataclass(frozen=True)
class ResumoDaIndexacao:
    novos: int = 0  # alertas que não tinham trechos e passaram a ter
    atualizados: int = 0  # alertas cujos trechos foram refeitos (conteúdo novo ou `tudo`)
    inalterados: int = 0
    metadados: int = 0  # só países, vigor ou classificação mudaram: sem vetorizar
    apagados: int = 0  # alertas que saíram da lista e perderam os trechos
    trechos: int = 0  # trechos vetorizados e gravados nesta passada
    falhas: int = 0


@dataclass(frozen=True)
class ResumoDaReindexacao:
    refeitos: int = 0  # alertas vetorizados com o modelo novo
    ja_completos: int = 0  # alertas que já tinham todos os vetores do modelo novo
    trechos_novos: int = 0
    vetores_antigos_apagados: int = 0
    apagados: int = 0  # alertas que saíram da lista e perderam os trechos
    falhas: int = 0


@dataclass(frozen=True)
class ModeloNoIndice:
    modelo: str
    dimensoes: int
    trechos: int
    alertas: int


@dataclass(frozen=True)
class SituacaoDoIndice:
    elegiveis: int
    indexados: int  # com todos os trechos do conteúdo atual, no modelo e na dimensão configurados
    modelos: tuple[ModeloNoIndice, ...]
    avisos: tuple[str, ...]

    @property
    def em_dia(self) -> bool:
        return self.indexados == self.elegiveis


# --------------------------------------------------------------------------- peças
def _com_os_citados(alerta: AlertaElegivel, citados: Citados | None) -> AlertaElegivel:
    """Num aviso geral, os países do índice são os que o título e o texto citam."""
    if alerta.paises or citados is None:
        return alerta
    citados_no_alerta = citados(f"{alerta.titulo}\n{alerta.texto}")
    return replace(alerta, paises=tuple(sorted(set(citados_no_alerta))))


def _vigor_do_alerta(alerta: AlertaElegivel, vigor: Vigor) -> tuple[str, ...]:
    return tuple(sorted(vigor.get(alerta.id, frozenset())))


def _tem_o_conteudo_atual(alerta: AlertaElegivel, atuais: list[TrechoGravado]) -> bool:
    return bool(atuais) and all(t.alerta_hash == alerta.hash for t in atuais)


def _metadados_desatualizados(
    alerta: AlertaElegivel, atuais: list[TrechoGravado], vigor: tuple[str, ...]
) -> bool:
    return any(
        t.paises != alerta.paises
        or t.em_vigor_para != vigor
        or t.classificacao_id != alerta.classificacao_id
        or t.indexado_em < alerta.classificado_em
        for t in atuais
    )


def _vetorizar_e_gravar(
    repo: TrechoAlertaRepositorio,
    embeddador: Embeddador,
    alerta: AlertaElegivel,
    vigor: tuple[str, ...],
    *,
    modelo: str,
    dimensoes: int,
    agora: datetime,
) -> int:
    """Fatia, vetoriza em lote e troca os trechos do alerta. Devolve quantos gravou."""
    intervalos = fatiar(alerta.texto, alerta.html_corpo)
    vetores = (
        embeddador.vetorizar_documentos([alerta.texto[i:f] for i, f in intervalos])
        if intervalos
        else []
    )
    if len(vetores) != len(intervalos):
        raise ErroDeEmbedding(f"{len(vetores)} vetores para {len(intervalos)} trechos")
    if any(len(vetor) != dimensoes for vetor in vetores):
        raise ErroDeEmbedding(f"o serviço devolveu vetores de outro tamanho que {dimensoes}")
    repo.substituir_trechos(
        alerta.id,
        alerta.hash,
        [
            NovoTrecho(i, inicio, fim, v)
            for i, ((inicio, fim), v) in enumerate(zip(intervalos, vetores, strict=True))
        ],
        modelo=modelo,
        dimensoes=dimensoes,
        classificacao_id=alerta.classificacao_id,
        paises=alerta.paises,
        em_vigor_para=vigor,
        agora=agora,
    )
    return len(intervalos)


def _atualizar_metadados(
    repo: TrechoAlertaRepositorio,
    alerta: AlertaElegivel,
    vigor: tuple[str, ...],
    *,
    modelo: str,
    dimensoes: int,
    agora: datetime,
) -> None:
    repo.atualizar_metadados(
        alerta.id,
        alerta.hash,
        modelo=modelo,
        dimensoes=dimensoes,
        classificacao_id=alerta.classificacao_id,
        paises=alerta.paises,
        em_vigor_para=vigor,
        agora=agora,
    )


# --------------------------------------------------------------------------- passada normal
def indexar_pendentes(
    sessao: Session,
    embeddador: Embeddador,
    vigor: Vigor,
    *,
    modelo: str,
    dimensoes: int,
    citados: Citados | None = None,
    tudo: bool = False,
    relogio: Relogio | None = None,
) -> ResumoDaIndexacao:
    """Uma passada: apaga o que saiu da lista, vetoriza o que é novo ou mudou e acerta o resto.

    `tudo` ignora a comparação e refaz os trechos do modelo configurado (por exemplo, depois de
    mudar o fatiamento); não mexe nos vetores de outros modelos.
    """
    agora = (relogio or RelogioDoSistema()).agora()
    repo = TrechoAlertaRepositorio(sessao)
    resumo = {
        "novos": 0,
        "atualizados": 0,
        "inalterados": 0,
        "metadados": 0,
        "trechos": 0,
        "falhas": 0,
    }
    apagados = repo.apagar_dos_que_nao_sao_elegiveis()
    gravados = repo.trechos_gravados(modelo, dimensoes)

    for alerta in repo.alertas_elegiveis():
        alerta = _com_os_citados(alerta, citados)
        atuais = gravados.get(alerta.id, [])
        do_vigor = _vigor_do_alerta(alerta, vigor)
        try:
            with sessao.begin_nested():
                if tudo or not _tem_o_conteudo_atual(alerta, atuais):
                    resumo["trechos"] += _vetorizar_e_gravar(
                        repo,
                        embeddador,
                        alerta,
                        do_vigor,
                        modelo=modelo,
                        dimensoes=dimensoes,
                        agora=agora,
                    )
                    resumo["atualizados" if atuais else "novos"] += 1
                elif _metadados_desatualizados(alerta, atuais, do_vigor):
                    _atualizar_metadados(
                        repo, alerta, do_vigor, modelo=modelo, dimensoes=dimensoes, agora=agora
                    )
                    resumo["metadados"] += 1
                else:
                    resumo["inalterados"] += 1
        except Exception as erro:
            # só o tipo do erro vai para o log: nem o texto do alerta nem a chave
            _log.warning("indexação do alerta %s falhou: %s", alerta.id, type(erro).__name__)
            resumo["falhas"] += 1
    return ResumoDaIndexacao(apagados=apagados, **resumo)


# --------------------------------------------------------------------------- troca de modelo
def reindexar(
    sessao: Session,
    embeddador: Embeddador,
    vigor: Vigor,
    *,
    modelo: str,
    dimensoes: int,
    citados: Citados | None = None,
    manter_antigos: bool = False,
    relogio: Relogio | None = None,
    andamento: Andamento | None = None,
) -> ResumoDaReindexacao:
    """Troca de modelo ou de dimensão: vetoriza tudo com o configurado e, só depois de cada alerta
    ficar completo, apaga os vetores dos outros modelos dele (a menos que `manter_antigos`).

    Um alerta que falha mantém os vetores antigos, então a busca nunca fica sem vetores no meio da
    troca. Rodar de novo não refaz o que já está completo.
    """
    agora = (relogio or RelogioDoSistema()).agora()
    repo = TrechoAlertaRepositorio(sessao)
    refeitos = ja_completos = trechos_novos = antigos_apagados = falhas = 0
    apagados = repo.apagar_dos_que_nao_sao_elegiveis()
    gravados = repo.trechos_gravados(modelo, dimensoes)

    elegiveis = [_com_os_citados(a, citados) for a in repo.alertas_elegiveis()]
    for posicao, alerta in enumerate(elegiveis, 1):
        atuais = gravados.get(alerta.id, [])
        do_vigor = _vigor_do_alerta(alerta, vigor)
        resultado = "falhou"
        try:
            with sessao.begin_nested():
                if _tem_o_conteudo_atual(alerta, atuais):
                    if _metadados_desatualizados(alerta, atuais, do_vigor):
                        _atualizar_metadados(
                            repo, alerta, do_vigor, modelo=modelo, dimensoes=dimensoes, agora=agora
                        )
                    ja_completos += 1
                    resultado = "completo"
                else:
                    trechos_novos += _vetorizar_e_gravar(
                        repo,
                        embeddador,
                        alerta,
                        do_vigor,
                        modelo=modelo,
                        dimensoes=dimensoes,
                        agora=agora,
                    )
                    refeitos += 1
                    resultado = "refeito"
                if not manter_antigos:
                    antigos_apagados += repo.apagar_de_outros_modelos(alerta.id, modelo, dimensoes)
        except Exception as erro:
            _log.warning("reindexação do alerta %s falhou: %s", alerta.id, type(erro).__name__)
            falhas += 1
        if andamento is not None:
            andamento(posicao, len(elegiveis), alerta.id, resultado)
    return ResumoDaReindexacao(
        refeitos=refeitos,
        ja_completos=ja_completos,
        trechos_novos=trechos_novos,
        vetores_antigos_apagados=antigos_apagados,
        apagados=apagados,
        falhas=falhas,
    )


# --------------------------------------------------------------------------- status
def consultar_situacao(sessao: Session, *, modelo: str, dimensoes: int) -> SituacaoDoIndice:
    """Só olha: alertas elegíveis × indexados, e o que o índice guarda por modelo e dimensão."""
    repo = TrechoAlertaRepositorio(sessao)
    elegiveis = repo.alertas_elegiveis()
    gravados = repo.trechos_gravados(modelo, dimensoes)
    indexados = sum(1 for a in elegiveis if _tem_o_conteudo_atual(a, gravados.get(a.id, [])))
    no_indice = tuple(ModeloNoIndice(m, d, t, a) for m, d, t, a in repo.resumo_do_indice())

    avisos: list[str] = []
    if no_indice and not any((m.modelo, m.dimensoes) == (modelo, dimensoes) for m in no_indice):
        guardados = ", ".join(f"{m.modelo} ({m.dimensoes} dimensões)" for m in no_indice)
        avisos.append(
            f"O índice só tem vetores de {guardados}; o configurado é {modelo} "
            f"({dimensoes} dimensões). Rode `reindexar`."
        )
    return SituacaoDoIndice(len(elegiveis), indexados, no_indice, tuple(avisos))
