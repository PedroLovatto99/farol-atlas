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

    def obter_com_soberano(self, codigo: str) -> list[Territorio]:
        """O território e o soberano dele, numa consulta só (nenhum se o código não existe)."""
        soberano = (
            select(Territorio.soberano_codigo).where(Territorio.codigo == codigo).scalar_subquery()
        )
        consulta = (
            select(Territorio)
            .where((Territorio.codigo == codigo) | (Territorio.codigo == soberano))
            .order_by(Territorio.codigo)
        )
        return list(self._sessao.scalars(consulta))

    def codigos_com_nivel(self) -> set[str]:
        """Códigos que podem ter nível: países e dependências (áreas neutras ficam de fora)."""
        consulta = select(Territorio.codigo).where(Territorio.tipo != TipoTerritorio.NEUTRO)
        return set(self._sessao.scalars(consulta))

    def adicionar(self, territorio: Territorio) -> None:
        self._sessao.add(territorio)
