"""Leitura e gravação de territórios (países, dependências e áreas neutras)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio.enums import TipoTerritorio
from farol.dominio.modelos import Territorio


class TerritorioRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def listar_todos(self) -> list[Territorio]:
        return list(self._sessao.scalars(select(Territorio).order_by(Territorio.codigo)))

    def obter(self, codigo: str) -> Territorio | None:
        return self._sessao.get(Territorio, codigo)

    def codigos_com_nivel(self) -> set[str]:
        """Códigos que podem ter nível: países e dependências (áreas neutras ficam de fora)."""
        consulta = select(Territorio.codigo).where(Territorio.tipo != TipoTerritorio.NEUTRO)
        return set(self._sessao.scalars(consulta))

    def adicionar(self, territorio: Territorio) -> None:
        self._sessao.add(territorio)
