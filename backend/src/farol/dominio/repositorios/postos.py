"""Leitura e gravação de postos brasileiros."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio.modelos import Posto


class PostoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def listar_todos(self) -> list[Posto]:
        return list(self._sessao.scalars(select(Posto).order_by(Posto.id)))

    def listar_por_territorio(self, codigo: str) -> list[Posto]:
        consulta = select(Posto).where(Posto.territorio_codigo == codigo).order_by(Posto.id)
        return list(self._sessao.scalars(consulta))

    def obter(self, posto_id: int) -> Posto | None:
        return self._sessao.get(Posto, posto_id)

    def adicionar(self, posto: Posto) -> None:
        self._sessao.add(posto)
