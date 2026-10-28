"""Leitura e gravação dos dados de vistos: coletas, requisitos, mudanças retidas e itens."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from farol.dominio.enums import (
    EstadoDaRetencao,
    EstadoDoItem,
    ResultadoDaColetaDeVistos,
    TipoDeItemParaRevisao,
)
from farol.dominio.modelos import ColetaVistos, ItemParaRevisao, MudancaRetida, RequisitoVisto

# Basta olhar o fim do histórico: as sequências que importam têm no máximo 3 tentativas
JANELA_DE_TENTATIVAS = 10


class ColetaVistosRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def adicionar(self, coleta: ColetaVistos) -> None:
        self._sessao.add(coleta)

    def obter(self, coleta_id: int) -> ColetaVistos | None:
        return self._sessao.get(ColetaVistos, coleta_id)

    def ultima_valida(self) -> ColetaVistos | None:
        """A última coleta válida: é dela que vêm os vistos exibidos (FR-010)."""
        consulta = (
            select(ColetaVistos)
            .where(
                ColetaVistos.resultado == ResultadoDaColetaDeVistos.VALIDA,
                ColetaVistos.finalizada_em.is_not(None),
            )
            .order_by(ColetaVistos.finalizada_em.desc(), ColetaVistos.id.desc())
            .limit(1)
        )
        return self._sessao.scalars(consulta).first()

    def ultima_tentativa(self) -> ColetaVistos | None:
        consulta = (
            select(ColetaVistos)
            .order_by(ColetaVistos.iniciada_em.desc(), ColetaVistos.id.desc())
            .limit(1)
        )
        return self._sessao.scalars(consulta).first()

    def adiadas_seguidas(self) -> int:
        """Quantas tentativas `adiada` há no fim do histórico, sem nenhuma outra no meio."""
        return self._seguidas(ResultadoDaColetaDeVistos.ADIADA)

    def falhas_seguidas(self) -> int:
        """Quantas tentativas `falhou` há no fim do histórico, sem nenhuma outra no meio."""
        return self._seguidas(ResultadoDaColetaDeVistos.FALHOU)

    # ------------------------------------------------------------------ internos
    def _seguidas(self, resultado: ResultadoDaColetaDeVistos) -> int:
        consulta = (
            select(ColetaVistos.resultado)
            .order_by(ColetaVistos.iniciada_em.desc(), ColetaVistos.id.desc())
            .limit(JANELA_DE_TENTATIVAS)
        )
        total = 0
        for atual in self._sessao.scalars(consulta):
            if atual is not resultado:
                break
            total += 1
        return total


class RequisitoVistoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def obter(self, codigo: str) -> RequisitoVisto | None:
        return self._sessao.get(RequisitoVisto, codigo)

    def listar(self, codigos: Sequence[str]) -> list[RequisitoVisto]:
        """Os registros dos `codigos` que têm um, numa consulta só."""
        consulta = (
            select(RequisitoVisto)
            .where(RequisitoVisto.territorio_codigo.in_(codigos))
            .order_by(RequisitoVisto.territorio_codigo)
        )
        return list(self._sessao.scalars(consulta))

    def listar_todos(self) -> list[RequisitoVisto]:
        consulta = select(RequisitoVisto).order_by(RequisitoVisto.territorio_codigo)
        return list(self._sessao.scalars(consulta))

    def adicionar(self, requisito: RequisitoVisto) -> None:
        """Registra o primeiro visto de um território (ao contrário de `salvar`, sem consultar)."""
        self._sessao.add(requisito)

    def salvar(self, requisito: RequisitoVisto) -> RequisitoVisto:
        """Grava o registro do território, criando ou substituindo o que já existe (upsert)."""
        return self._sessao.merge(requisito)

    def remover(self, requisito: RequisitoVisto) -> None:
        """Apaga o registro: a fonte deixou de trazer a linha e o território fica sem informação."""
        self._sessao.delete(requisito)


class MudancaRetidaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def adicionar(self, mudanca: MudancaRetida) -> None:
        self._sessao.add(mudanca)

    def pendente_do(self, codigo: str) -> MudancaRetida | None:
        return self._do_territorio(codigo, EstadoDaRetencao.PENDENTE)

    def rejeitada_do(self, codigo: str) -> MudancaRetida | None:
        return self._do_territorio(codigo, EstadoDaRetencao.REJEITADA)

    def listar_pendentes(self) -> list[MudancaRetida]:
        return self._listar(EstadoDaRetencao.PENDENTE)

    def listar_rejeitadas(self) -> list[MudancaRetida]:
        return self._listar(EstadoDaRetencao.REJEITADA)

    def atualizar_coleta(self, mudanca: MudancaRetida, coleta_id: int) -> None:
        """A fonte manteve o mesmo valor retido: só aponta para a coleta que o viu por último."""
        self._exigir_pendente(mudanca, "atualizar")
        mudanca.coleta_id = coleta_id

    def confirmar(self, mudanca: MudancaRetida, em: datetime) -> None:
        """O dono confirmou. Quem chama grava o candidato em `requisito_visto`."""
        self._exigir_pendente(mudanca, "confirmar")
        self._encerrar(mudanca, EstadoDaRetencao.CONFIRMADA, em)

    def rejeitar(self, mudanca: MudancaRetida, em: datetime) -> None:
        self._exigir_pendente(mudanca, "rejeitar")
        self._encerrar(mudanca, EstadoDaRetencao.REJEITADA, em)

    def reverter(self, mudanca: MudancaRetida, em: datetime) -> None:
        """A fonte voltou ao valor exibido."""
        self._exigir_aberta(mudanca, "reverter")
        self._encerrar(mudanca, EstadoDaRetencao.REVERTIDA, em)

    def superar(self, mudanca: MudancaRetida, em: datetime) -> None:
        """A fonte mudou para outro valor: a decisão recomeça."""
        self._exigir_aberta(mudanca, "superar")
        self._encerrar(mudanca, EstadoDaRetencao.SUPERADA, em)

    # ------------------------------------------------------------------ internos
    def _listar(self, estado: EstadoDaRetencao) -> list[MudancaRetida]:
        consulta = (
            select(MudancaRetida)
            .where(MudancaRetida.estado == estado)
            .order_by(MudancaRetida.territorio_codigo)
        )
        return list(self._sessao.scalars(consulta))

    def _do_territorio(self, codigo: str, estado: EstadoDaRetencao) -> MudancaRetida | None:
        consulta = select(MudancaRetida).where(
            MudancaRetida.territorio_codigo == codigo, MudancaRetida.estado == estado
        )
        return self._sessao.scalars(consulta).first()

    @staticmethod
    def _exigir_pendente(mudanca: MudancaRetida, acao: str) -> None:
        if mudanca.estado is not EstadoDaRetencao.PENDENTE:
            raise ValueError(
                f"só uma mudança pendente pode {acao} (a de {mudanca.territorio_codigo} "
                f"está {mudanca.estado.value})"
            )

    @staticmethod
    def _exigir_aberta(mudanca: MudancaRetida, acao: str) -> None:
        if mudanca.estado not in (EstadoDaRetencao.PENDENTE, EstadoDaRetencao.REJEITADA):
            raise ValueError(
                f"só uma mudança aberta (pendente ou rejeitada) pode {acao} (a de "
                f"{mudanca.territorio_codigo} está {mudanca.estado.value})"
            )

    @staticmethod
    def _encerrar(mudanca: MudancaRetida, estado: EstadoDaRetencao, em: datetime) -> None:
        mudanca.estado = estado
        mudanca.resolvida_em = em


class ItemParaRevisaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def obter(self, tipo: TipoDeItemParaRevisao, valor: str) -> ItemParaRevisao | None:
        consulta = select(ItemParaRevisao).where(
            ItemParaRevisao.tipo == tipo, ItemParaRevisao.valor == valor
        )
        return self._sessao.scalars(consulta).first()

    def listar_pendentes(self, tipo: TipoDeItemParaRevisao | None = None) -> list[ItemParaRevisao]:
        consulta = select(ItemParaRevisao).where(ItemParaRevisao.estado == EstadoDoItem.PENDENTE)
        if tipo is not None:
            consulta = consulta.where(ItemParaRevisao.tipo == tipo)
        consulta = consulta.order_by(ItemParaRevisao.tipo, ItemParaRevisao.valor)
        return list(self._sessao.scalars(consulta))

    def registrar_visto(
        self, tipo: TipoDeItemParaRevisao, valor: str, contexto: Any, em: datetime
    ) -> ItemParaRevisao:
        """O item apareceu na coleta de `em`: cria como pendente, ou atualiza o que já existe.

        Um item `resolvido` que reaparece volta a `pendente`; um `ignorado` continua ignorado.
        """
        item = self.obter(tipo, valor)
        if item is None:
            item = ItemParaRevisao(
                tipo=tipo,
                valor=valor,
                contexto=contexto,
                primeira_vez_em=em,
                ultima_vez_em=em,
                estado=EstadoDoItem.PENDENTE,
            )
            self._sessao.add(item)
            return item
        item.contexto = contexto
        item.ultima_vez_em = em
        if item.estado is EstadoDoItem.RESOLVIDO:
            item.estado = EstadoDoItem.PENDENTE
            item.resolvido_em = None
        return item

    def resolver_nao_vistos(self, visto_em: datetime, em: datetime) -> int:
        """Resolve os itens pendentes que a coleta de `visto_em` não viu; devolve quantos."""
        # Os itens vistos nesta coleta ainda podem estar só na sessão: grava antes de comparar
        self._sessao.flush()
        comando = (
            update(ItemParaRevisao)
            .where(
                ItemParaRevisao.estado == EstadoDoItem.PENDENTE,
                ItemParaRevisao.ultima_vez_em < visto_em,
            )
            .values(estado=EstadoDoItem.RESOLVIDO, resolvido_em=em)
            .execution_options(synchronize_session="fetch")
        )
        return cast("CursorResult[Any]", self._sessao.execute(comando)).rowcount

    def ignorar_nome(self, item: ItemParaRevisao, motivo: str, em: datetime) -> None:
        """Ignora um nome pendente, com motivo. Rótulo e regra não podem ser ignorados."""
        if item.tipo is not TipoDeItemParaRevisao.NOME:
            raise ValueError(f"só um nome pode ser ignorado (este é do tipo {item.tipo.value})")
        if item.estado is not EstadoDoItem.PENDENTE:
            raise ValueError(
                f"só um item pendente pode ser ignorado (este está {item.estado.value})"
            )
        if not motivo.strip():
            raise ValueError("informe o motivo para ignorar o nome")
        item.estado = EstadoDoItem.IGNORADO
        item.motivo_ignorar = motivo.strip()
        item.resolvido_em = em
