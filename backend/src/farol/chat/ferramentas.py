"""Ferramentas que o agente oferece ao modelo (contracts/ferramentas-do-chat.md, seção 3).

Todas só leem. O argumento `pais` é validado pelo código contra os países que o próprio código
achou na pergunta (D6): o modelo não escolhe de que país se fala. O texto devolvido ao modelo vai
dentro de um bloco `<<<DADOS … >>>` e é dado, nunca ordem; o artefato que o código guarda (o texto
original do trecho, caractere a caractere) é o que alimenta as citações.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from langchain_core.tools import BaseTool, tool

from farol.chat.protocolos import ConsultaDeNivel, PaisEncontrado
from farol.chat.recuperacao import TrechoEncontrado
from farol.dominio import AlertaCitado
from farol.infra import FUSO_DE_BRASILIA

ABRE = "<<<"
FECHA = ">>>"

Vigor = Literal["em_vigor", "anterior"]


class Recuperador(Protocol):
    def recuperar(
        self, pergunta: str, paises: Sequence[str] | None = None
    ) -> list[TrechoEncontrado]: ...


class FonteDeAlertas(Protocol):
    def alertas_citados(self, ids: Sequence[int]) -> dict[int, AlertaCitado]: ...


@dataclass(frozen=True)
class TrechoUsado:
    """Um trecho de alerta entregue ao modelo; vira uma citação com "Ver trecho"."""

    alerta_id: int
    titulo: str
    data: datetime  # modificado_em ou, na falta, publicado_em (FR-007b)
    url: str
    vigor: Vigor
    inicio: int
    fim: int
    trecho: str  # exatamente `alerta.texto[inicio:fim]`


@dataclass
class ContextoDaPergunta:
    """O que as ferramentas de UMA pergunta enxergam: os países do código e as fontes de dados."""

    paises: tuple[PaisEncontrado, ...]
    recuperador: Recuperador
    consulta_de_nivel: ConsultaDeNivel
    alertas: FonteDeAlertas
    contar: Callable[[str], None] = lambda chave: None
    limite_de_trechos: int = 4


def _neutralizar(texto: str) -> str:
    """O texto do alerta não pode fechar o bloco de dados antes da hora."""
    return texto.replace(ABRE, "«").replace(FECHA, "»")


def _dia(instante: datetime) -> str:
    return instante.astimezone(FUSO_DE_BRASILIA).strftime("%d/%m/%Y")


def criar_ferramentas(contexto: ContextoDaPergunta) -> list[BaseTool]:
    permitidos = {p.codigo for p in contexto.paises}
    # a dependência herda os alertas do soberano (FR-031): eles citam o soberano, não a dependência
    busca_em = sorted(permitidos | {p.soberano for p in contexto.paises if p.soberano})

    @tool("buscar_nos_alertas", response_format="content_and_artifact")
    def buscar_nos_alertas(consulta: str, pais: str | None = None) -> tuple[str, list[TrechoUsado]]:
        """Busca, nos alertas consulares do Itamaraty, os trechos que respondem à pergunta.

        `consulta` é o assunto a procurar, em português. `pais` é o código do país (por exemplo
        "IR"); deixe vazio para buscar em todos os países da pergunta. Devolve até 4 trechos, cada
        um com título, data e se o alerta está em vigor ou é anterior, e o texto original.
        """
        if pais is not None:
            codigo = pais.strip().upper()
            if codigo not in permitidos:
                contexto.contar("pais_invalido_pedido")
                return f"País não permitido nesta pergunta: {pais!r}. Nada foi buscado.", []
            filtro = [codigo]
        else:
            filtro = busca_em
        contexto.contar("ferramenta_alertas")

        achados = contexto.recuperador.recuperar(consulta, filtro)[: contexto.limite_de_trechos]
        if not achados:
            return "Nenhum trecho de alerta responde a essa busca.", []

        alertas = contexto.alertas.alertas_citados(sorted({a.alerta_id for a in achados}))
        regentes: set[int] = set()
        for codigo in filtro:
            if codigo in permitidos:  # o soberano só entra no filtro; o nível é do território
                rege = contexto.consulta_de_nivel.consultar(codigo).alerta_que_rege
                if rege is not None:
                    regentes.add(rege.id)

        usados: list[TrechoUsado] = []
        for achado in achados:
            alerta = alertas.get(achado.alerta_id)
            if alerta is None:
                continue
            usados.append(
                TrechoUsado(
                    alerta_id=alerta.id,
                    titulo=alerta.titulo,
                    data=alerta.modificado_em or alerta.publicado_em,
                    url=alerta.url,
                    vigor="em_vigor" if alerta.id in regentes else "anterior",
                    inicio=achado.inicio,
                    fim=achado.fim,
                    trecho=alerta.texto[achado.inicio : achado.fim],
                )
            )
        blocos = [
            f"[{n}] {_neutralizar(u.titulo)} ({_dia(u.data)}) — "
            + ("EM VIGOR" if u.vigor == "em_vigor" else "ANTERIOR (não é o alerta que vale hoje)")
            + f"\n{_neutralizar(u.trecho)}"
            for n, u in enumerate(usados, 1)
        ]
        return f"{ABRE}DADOS\n" + "\n\n".join(blocos) + f"\n{FECHA}", usados

    return [buscar_nos_alertas]
