"""Contagens anônimas do chat: um contador por dia e por tipo de evento (nunca texto nem IP)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from farol.dominio.modelos import ContagemChat

FUSO_DE_BRASILIA = ZoneInfo("America/Sao_Paulo")


def dia_em_brasilia(instante: datetime) -> date:
    """O dia (horário de Brasília) em que cai o instante, que é a chave dos contadores."""
    return instante.astimezone(FUSO_DE_BRASILIA).date()


class ContagemChatRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def valor(self, chave: str, dia: date) -> int:
        consulta = select(ContagemChat.valor).where(
            ContagemChat.dia == dia, ContagemChat.chave == chave
        )
        return self._sessao.scalars(consulta).first() or 0

    def incrementar(self, chave: str, dia: date, quantidade: int = 1) -> int:
        """Soma `quantidade` ao contador (criando-o se preciso) e devolve o valor novo."""
        comando = (
            insert(ContagemChat)
            .values(dia=dia, chave=chave, valor=quantidade)
            .on_conflict_do_update(
                index_elements=[ContagemChat.dia, ContagemChat.chave],
                set_={"valor": ContagemChat.valor + quantidade},
            )
            .returning(ContagemChat.valor)
        )
        valor: int = self._sessao.execute(comando).scalar_one()
        return valor

    def reservar(self, chave: str, dia: date, teto: int) -> bool:
        """Reserva uma vaga de forma atômica: só soma se o valor ainda está abaixo do teto."""
        if teto <= 0:
            return False
        self._sessao.execute(
            insert(ContagemChat)
            .values(dia=dia, chave=chave, valor=0)
            .on_conflict_do_nothing(index_elements=[ContagemChat.dia, ContagemChat.chave])
        )
        comando = (
            update(ContagemChat)
            .where(ContagemChat.dia == dia, ContagemChat.chave == chave, ContagemChat.valor < teto)
            .values(valor=ContagemChat.valor + 1)
            .returning(ContagemChat.valor)
        )
        return self._sessao.execute(comando).first() is not None

    def devolver(self, chave: str, dia: date) -> None:
        """Devolve uma vaga reservada (nunca deixa o contador abaixo de zero)."""
        self._sessao.execute(
            update(ContagemChat)
            .where(ContagemChat.dia == dia, ContagemChat.chave == chave)
            .values(valor=func.greatest(ContagemChat.valor - 1, 0))
        )
