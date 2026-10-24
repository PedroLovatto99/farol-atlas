"""Coleta dos alertas do Portal Consular: lê a lista, abre cada alerta, grava e confirma.

Regras (spec FR-008, FR-008a, FR-040; data-model.md):

- Toda rodada abre a página de todos os alertas da lista, com a pausa do cliente educado.
- O que a coleta lê vai para as colunas comuns de `alerta`. Só ao fim de uma execução COMPLETA
  a leitura é copiada para as colunas `confirmado_*`, as únicas que valem para o nível.
- Completa = lista lida inteira (nenhum link de próxima página falhou), com pelo menos um alerta,
  pelo menos 70% das páginas lidas e sem bloqueio nem verificação humana no meio do caminho.
- Remoção (`removido_em`) só numa execução completa.
"""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from farol.coleta.cliente_educado import Pagina
from farol.coleta.extratores import (
    AlertaExtraido,
    ErroDeExtracao,
    ItemDaLista,
    extrair_alerta,
    extrair_lista_de_alertas,
)
from farol.dominio import (
    Alerta,
    AlertaRepositorio,
    ExecucaoColeta,
    ExecucaoRepositorio,
    TipoExecucao,
)
from farol.infra import Relogio, obter_logger

URL_LISTA_DE_ALERTAS = (
    "https://www.gov.br/mre/pt-br/assuntos/portal-consular/alertas%20e%20noticias/alertas"
)
FUSO_DO_PORTAL = ZoneInfo("America/Sao_Paulo")
LIMITE_DE_PAGINAS_DA_LISTA = 50  # trava contra um link de próxima página que nunca acaba
MINIMO_LIDO = (7, 10)  # 70% das páginas esperadas (FR-040), em conta de inteiros

_log = obter_logger("farol.coleta")


class Baixador(Protocol):
    """O que o serviço precisa do cliente HTTP (`ClienteEducado` ou um falso nos testes)."""

    interrompido_por: str | None

    def baixar(self, url: str) -> Pagina: ...


@dataclass(frozen=True)
class ResultadoDaColeta:
    execucao_id: int
    completa: bool
    motivo_interrupcao: str | None
    paginas_esperadas: int
    paginas_lidas: int
    para_classificar: tuple[int, ...]  # alertas novos ou alterados lidos nesta rodada
    removidos: int


def _normalizar(texto: str) -> str:
    return " ".join(texto.split())


def hash_do_alerta(titulo: str, texto: str) -> str:
    """SHA-256 de título e texto, com os espaços normalizados."""
    conteudo = f"{_normalizar(titulo)}\n{_normalizar(texto)}"
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


def _dia_local(instante: datetime) -> object:
    return instante.astimezone(FUSO_DO_PORTAL).date()


@dataclass
class _Lista:
    itens: list[ItemDaLista]
    inteira: bool
    motivo: str | None


class ServicoDeColetaDeAlertas:
    def __init__(
        self,
        sessao: Session,
        cliente: Baixador,
        relogio: Relogio,
        *,
        url_da_lista: str = URL_LISTA_DE_ALERTAS,
    ) -> None:
        self._sessao = sessao
        self._cliente = cliente
        self._relogio = relogio
        self._url_da_lista = url_da_lista
        self._alertas = AlertaRepositorio(sessao)
        self._execucoes = ExecucaoRepositorio(sessao)

    def coletar(self) -> ResultadoDaColeta:
        agora = self._relogio.agora()
        execucao = ExecucaoColeta(tipo=TipoExecucao.ALERTAS, iniciada_em=agora)
        self._execucoes.adicionar(execucao)
        self._sessao.flush()

        lista = self._ler_lista()
        lidos = self._ler_alertas(lista.itens)
        motivo = self._cliente.interrompido_por or lista.motivo

        esperadas = len(lista.itens)
        lidas = len(lidos)
        suficiente = esperadas >= 1 and lidas * MINIMO_LIDO[1] >= esperadas * MINIMO_LIDO[0]
        if motivo is None and esperadas >= 1 and not suficiente:
            motivo = f"só {lidas} de {esperadas} páginas lidas (mínimo de 70%)"
        completa = lista.inteira and self._cliente.interrompido_por is None and suficiente

        existentes = {a.url: a for a in self._alertas.listar_todos()}
        gravados: list[tuple[Alerta, bool]] = []
        for item in lista.itens:
            gravados.append(
                self._gravar(item, lidos.get(item.url), existentes.get(item.url), agora)
            )
        self._sessao.flush()

        removidos = 0
        if completa:
            self._confirmar(execucao, gravados, set(lidos))
            removidos = self._marcar_removidos(existentes, {i.url for i in lista.itens}, agora)

        execucao.finalizada_em = self._relogio.agora()
        execucao.paginas_esperadas = esperadas
        execucao.paginas_lidas = lidas
        execucao.lista_lida_inteira = lista.inteira
        execucao.completa = completa
        execucao.motivo_interrupcao = None if completa else motivo
        self._sessao.flush()

        _log.info(
            "coleta de alertas %s: %d de %d páginas lidas%s",
            "completa" if completa else "INCOMPLETA",
            lidas,
            esperadas,
            "" if completa else f" ({motivo})",
        )
        return ResultadoDaColeta(
            execucao_id=execucao.id,
            completa=completa,
            motivo_interrupcao=execucao.motivo_interrupcao,
            paginas_esperadas=esperadas,
            paginas_lidas=lidas,
            para_classificar=tuple(a.id for a, mudou in gravados if mudou),
            removidos=removidos,
        )

    # ------------------------------------------------------------------ lista
    def _ler_lista(self) -> _Lista:
        itens: dict[str, ItemDaLista] = {}
        url: str | None = self._url_da_lista
        visitadas: set[str] = set()
        primeira = True
        while (
            url is not None and url not in visitadas and len(visitadas) < LIMITE_DE_PAGINAS_DA_LISTA
        ):
            visitadas.add(url)
            pagina = self._cliente.baixar(url)
            if not pagina.ok:
                quando = "a lista de alertas" if primeira else "a próxima página da lista"
                return _Lista(list(itens.values()), False, f"não leu {quando} ({pagina.motivo})")
            lista = extrair_lista_de_alertas(pagina.html, url)
            for item in lista.itens:
                itens.setdefault(item.url, item)
            url = lista.proxima_pagina
            primeira = False
        if url is not None:
            return _Lista(
                list(itens.values()), False, "não leu a próxima página da lista (páginas demais)"
            )
        if not itens:
            return _Lista([], False, "lista em formato inesperado (nenhum alerta encontrado)")
        return _Lista(list(itens.values()), True, None)

    # ------------------------------------------------------------------ alertas
    def _ler_alertas(self, itens: list[ItemDaLista]) -> dict[str, AlertaExtraido]:
        lidos: dict[str, AlertaExtraido] = {}
        for item in itens:
            if self._cliente.interrompido_por is not None:
                break  # bloqueio ou verificação humana: nunca insiste
            pagina = self._cliente.baixar(item.url)
            if not pagina.ok:
                _log.warning("alerta não lido (%s): %s", pagina.motivo, item.url)
                continue
            try:
                lidos[item.url] = extrair_alerta(pagina.html)
            except ErroDeExtracao as erro:
                _log.warning("alerta fora do formato esperado (%s): %s", erro, item.url)
        return lidos

    def _gravar(
        self,
        item: ItemDaLista,
        lido: AlertaExtraido | None,
        existente: Alerta | None,
        agora: datetime,
    ) -> tuple[Alerta, bool]:
        """Grava a leitura. Devolve o alerta e se é novo ou alterado (para classificar)."""
        if lido is not None:
            novo_hash = hash_do_alerta(lido.titulo, lido.texto)
            campos = {
                "titulo": lido.titulo,
                "texto": lido.texto,
                "html_corpo": lido.html_corpo,
                "categoria": lido.categoria,
                "publicado_em": lido.publicado_em,
                "modificado_em": lido.modificado_em,
                "hash": novo_hash,
                "pagina_lida": True,
            }
            if existente is None:
                alerta = Alerta(
                    url=item.url, primeira_coleta_em=agora, ultima_coleta_em=agora, **campos
                )
                self._alertas.adicionar(alerta)
                return alerta, True
            mudou = existente.hash != novo_hash
            self._aplicar(existente, campos, agora)
            return existente, mudou

        campos_da_lista = {
            "titulo": item.titulo,
            "texto": None,
            "html_corpo": None,
            "modificado_em": None,
            "publicado_em": item.publicado_em,
            "hash": None,
            "pagina_lida": False,
        }
        if existente is None:
            alerta = Alerta(
                url=item.url, primeira_coleta_em=agora, ultima_coleta_em=agora, **campos_da_lista
            )
            self._alertas.adicionar(alerta)
            return alerta, False
        if self._e_o_mesmo(existente, item):  # FR-008a: continua valendo o que já se sabe
            existente.ultima_coleta_em = agora
            existente.removido_em = None
        else:
            self._aplicar(existente, campos_da_lista, agora)
        return existente, False

    @staticmethod
    def _e_o_mesmo(existente: Alerta, item: ItemDaLista) -> bool:
        """Mesma URL, mesmo dia de publicação na lista e conteúdo já conhecido."""
        return existente.hash is not None and _dia_local(existente.publicado_em) == _dia_local(
            item.publicado_em
        )

    @staticmethod
    def _aplicar(alerta: Alerta, campos: Mapping[str, object], agora: datetime) -> None:
        for nome, valor in campos.items():
            setattr(alerta, nome, valor)
        alerta.ultima_coleta_em = agora
        alerta.removido_em = None

    # ------------------------------------------------------------------ confirmação e remoção
    def _confirmar(
        self,
        execucao: ExecucaoColeta,
        gravados: list[tuple[Alerta, bool]],
        lidos_agora: set[str],
    ) -> None:
        """Copia a leitura para `confirmado_*` (só em execução completa)."""
        for alerta, _ in gravados:
            lido_agora = alerta.url in lidos_agora
            conhecido = alerta.hash is not None
            if lido_agora or (conhecido and alerta.confirmado_execucao_id is None):
                self._copiar_leitura(alerta, execucao.id)
            elif conhecido:
                alerta.confirmado_execucao_id = execucao.id  # o mesmo alerta: nada muda no nível
            else:  # novo ou alterado e não lido: pendente, identificado pelo título da lista
                alerta.confirmado_execucao_id = execucao.id
                alerta.confirmado_hash = None
                alerta.confirmado_titulo = alerta.titulo
                alerta.confirmado_data_ref = alerta.publicado_em

    @staticmethod
    def _copiar_leitura(alerta: Alerta, execucao_id: int) -> None:
        alerta.confirmado_execucao_id = execucao_id
        alerta.confirmado_hash = alerta.hash
        alerta.confirmado_titulo = alerta.titulo
        alerta.confirmado_data_ref = alerta.modificado_em or alerta.publicado_em

    @staticmethod
    def _marcar_removidos(
        existentes: dict[str, Alerta], urls_da_lista: set[str], agora: datetime
    ) -> int:
        removidos = 0
        for url, alerta in existentes.items():
            if url not in urls_da_lista and alerta.removido_em is None:
                alerta.removido_em = agora
                removidos += 1
        return removidos
