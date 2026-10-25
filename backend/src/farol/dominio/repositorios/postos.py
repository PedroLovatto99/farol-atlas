"""Leitura e gravação de postos brasileiros."""

from collections.abc import Sequence

from sqlalchemy import or_, select
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

    def listar_para_painel(
        self, codigos: Sequence[str], ids_extras: Sequence[int] = ()
    ) -> list[Posto]:
        """Postos dos países `codigos` mais os de `ids_extras` (o responsável, em outro país), numa
        consulta só."""
        consulta = (
            select(Posto)
            .where(or_(Posto.territorio_codigo.in_(codigos), Posto.id.in_(ids_extras)))
            .order_by(Posto.id)
        )
        return list(self._sessao.scalars(consulta))

    def obter(self, posto_id: int) -> Posto | None:
        return self._sessao.get(Posto, posto_id)

    def adicionar(self, posto: Posto) -> None:
        self._sessao.add(posto)
