"""Leitura e gravação de postos brasileiros."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, or_, select
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

    def registrar_contato(
        self,
        posto: Posto,
        *,
        endereco: str | None,
        telefone_plantao: str | None,
        coletado_em: datetime,
        fonte_url: str,
    ) -> None:
        """Grava endereço, telefone, data e fonte juntos (princípio V: nada sem fonte e data)."""
        posto.endereco = endereco
        posto.telefone_plantao = telefone_plantao
        posto.contato_coletado_em = coletado_em
        posto.contato_fonte_url = fonte_url

    def contar_com_contato(self) -> tuple[int, int]:
        """Cobertura da coleta: quantos postos têm endereço e quantos têm telefone de plantão."""
        consulta = select(func.count(Posto.endereco), func.count(Posto.telefone_plantao))
        com_endereco, com_telefone = self._sessao.execute(consulta).one()
        return com_endereco, com_telefone
