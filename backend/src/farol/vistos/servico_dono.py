"""Meios do dono (restritos, sem exposição pública): ver pendências, confirmar, rejeitar, ignorar.

O que a coleta deixa esperando o dono (FR-010a, FR-012b): mudanças retidas, nomes e rótulos que não
reconheceu e regras por país a reconfirmar. Quem chama é o comando do worker, dentro do contêiner.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from farol.dominio import (
    CategoriaDeVisto,
    ColetaVistosRepositorio,
    EstadoDoItem,
    ItemParaRevisao,
    ItemParaRevisaoRepositorio,
    MudancaRetida,
    MudancaRetidaRepositorio,
    RequisitoVisto,
    RequisitoVistoRepositorio,
    TipoDeItemParaRevisao,
)
from farol.infra import Relogio
from farol.vistos.normalizacao import chave_de_consulta
from farol.vistos.registro import preencher_requisito


class ErroDoDono(Exception):
    """Pedido que não pode ser atendido: sem mudança retida, nome não pendente ou sem motivo."""


@dataclass(frozen=True)
class MudancaPendente:
    codigo: str
    categoria_exibida: CategoriaDeVisto | None  # nulo = "sem informação"
    categoria_lida: CategoriaDeVisto | None
    aceita_rg_exibido: bool
    aceita_rg_lido: bool
    desde: datetime  # quando a mudança foi retida
    dado_exibido_de: datetime | None  # a data do dado que o painel ainda mostra


@dataclass(frozen=True)
class ItemPendente:
    tipo: TipoDeItemParaRevisao
    valor: str  # normalizado
    contexto: Any  # onde apareceu: lista de {tabela, nome_na_fonte, ...}
    primeira_vez_em: datetime
    ultima_vez_em: datetime


@dataclass(frozen=True)
class RegraPendente:
    codigo: str
    hash_esperado: str  # o que está em `regras_por_pais.yaml`
    hash_lido: str  # o que a fonte traz hoje: é o valor para colar no arquivo
    texto: str  # a nota nova, para o dono decidir
    primeira_vez_em: datetime
    ultima_vez_em: datetime


@dataclass(frozen=True)
class PendenciasDoDono:
    retidas: tuple[MudancaPendente, ...]
    nomes: tuple[ItemPendente, ...]
    rotulos: tuple[ItemPendente, ...]
    regras: tuple[RegraPendente, ...]

    @property
    def total(self) -> int:
        return len(self.retidas) + len(self.nomes) + len(self.rotulos) + len(self.regras)


def _resumir(mudanca: MudancaRetida, exibido: RequisitoVisto | None) -> MudancaPendente:
    return MudancaPendente(
        codigo=mudanca.territorio_codigo,
        categoria_exibida=mudanca.categoria_exibida,
        categoria_lida=mudanca.categoria_lida,
        aceita_rg_exibido=mudanca.aceita_rg_exibido,
        aceita_rg_lido=mudanca.aceita_rg_lido,
        desde=mudanca.criada_em,
        dado_exibido_de=exibido.lido_em if exibido else None,
    )


def _item(item: ItemParaRevisao) -> ItemPendente:
    return ItemPendente(
        tipo=item.tipo,
        valor=item.valor,
        contexto=item.contexto,
        primeira_vez_em=item.primeira_vez_em,
        ultima_vez_em=item.ultima_vez_em,
    )


def _regra(item: ItemParaRevisao) -> RegraPendente:
    return RegraPendente(
        codigo=item.valor,
        hash_esperado=item.contexto["hash_esperado"],
        hash_lido=item.contexto["hash_lido"],
        texto=item.contexto["texto"],
        primeira_vez_em=item.primeira_vez_em,
        ultima_vez_em=item.ultima_vez_em,
    )


class ServicoDoDono:
    def __init__(self, sessao: Session, relogio: Relogio) -> None:
        self._sessao = sessao
        self._relogio = relogio
        self._coletas = ColetaVistosRepositorio(sessao)
        self._requisitos = RequisitoVistoRepositorio(sessao)
        self._mudancas = MudancaRetidaRepositorio(sessao)
        self._itens = ItemParaRevisaoRepositorio(sessao)

    # ------------------------------------------------------------------ listar
    def listar_pendentes(self) -> PendenciasDoDono:
        mudancas = self._mudancas.listar_pendentes()
        exibidos = {
            r.territorio_codigo: r
            for r in self._requisitos.listar([m.territorio_codigo for m in mudancas])
        }
        itens = self._itens.listar_pendentes()
        return PendenciasDoDono(
            retidas=tuple(_resumir(m, exibidos.get(m.territorio_codigo)) for m in mudancas),
            nomes=tuple(_item(i) for i in itens if i.tipo is TipoDeItemParaRevisao.NOME),
            rotulos=tuple(_item(i) for i in itens if i.tipo is TipoDeItemParaRevisao.ROTULO),
            regras=tuple(_regra(i) for i in itens if i.tipo is TipoDeItemParaRevisao.REGRA),
        )

    # ------------------------------------------------------------------ mudanças retidas
    def _retida_de(self, codigo: str) -> tuple[str, MudancaRetida]:
        chave = codigo.strip().upper()
        mudanca = self._mudancas.pendente_do(chave)
        if mudanca is None:
            raise ErroDoDono(
                f"{chave}: não há mudança retida esperando confirmação (veja `vistos pendentes`)"
            )
        return chave, mudanca

    def confirmar(self, codigo: str) -> MudancaPendente:
        """O candidato retido vira o dado exibido, com a data da coleta que o leu."""
        chave, mudanca = self._retida_de(codigo)
        coleta = self._coletas.obter(mudanca.coleta_id)
        if coleta is None:  # a chave estrangeira garante; isto só aplaca o tipo
            raise ErroDoDono(f"{chave}: a coleta que leu a mudança não foi encontrada")
        exibido = self._requisitos.obter(chave)
        resumo = _resumir(mudanca, exibido)
        if mudanca.categoria_lida is None:  # a linha saiu da fonte: o país fica sem informação
            if exibido is not None:
                self._requisitos.remover(exibido)
        elif exibido is None:
            novo = RequisitoVisto(territorio_codigo=chave)
            preencher_requisito(novo, mudanca.candidato, coleta.iniciada_em, coleta.id)
            self._requisitos.adicionar(novo)
        else:
            preencher_requisito(exibido, mudanca.candidato, coleta.iniciada_em, coleta.id)
        self._mudancas.confirmar(mudanca, self._relogio.agora())
        self._sessao.flush()
        return resumo

    def confirmar_todos(self) -> tuple[str, ...]:
        """Confirma todas as mudanças retidas; devolve os códigos, em ordem."""
        codigos = [m.territorio_codigo for m in self._mudancas.listar_pendentes()]
        for codigo in codigos:
            self.confirmar(codigo)
        return tuple(codigos)

    def rejeitar(self, codigo: str) -> None:
        """Rejeita a mudança: vale enquanto a fonte mantiver o mesmo valor lido."""
        _, mudanca = self._retida_de(codigo)
        self._mudancas.rejeitar(mudanca, self._relogio.agora())
        self._sessao.flush()

    # ------------------------------------------------------------------ nomes
    def ignorar_nome(self, nome: str, motivo: str) -> None:
        """Ignora de propósito um nome pendente. Rótulo e regra por país não podem ser ignorados."""
        if not motivo.strip():
            raise ErroDoDono("informe o motivo para ignorar o nome")
        item = self._itens.obter(TipoDeItemParaRevisao.NOME, chave_de_consulta(nome))
        if item is None or item.estado is not EstadoDoItem.PENDENTE:
            raise ErroDoDono(
                f"{nome!r} não é um nome pendente (só um nome não reconhecido pode ser ignorado; "
                "veja `vistos pendentes`)"
            )
        self._itens.ignorar_nome(item, motivo, self._relogio.agora())
        self._sessao.flush()
