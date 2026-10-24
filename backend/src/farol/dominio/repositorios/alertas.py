"""Leitura e gravação de alertas, com suas classificações."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from farol.dominio.modelos import Alerta, Classificacao


class AlertaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def listar_confirmados_ativos(self) -> list[Alerta]:
        """Alertas confirmados por uma coleta completa e ainda na lista (os que valem para o nível).

        Carrega classificações e níveis de uma vez: 3 consultas, qualquer que seja o número de
        alertas (sem N+1).
        """
        consulta = (
            select(Alerta)
            .where(Alerta.confirmado_execucao_id.is_not(None), Alerta.removido_em.is_(None))
            .options(selectinload(Alerta.classificacoes).selectinload(Classificacao.niveis))
            .order_by(Alerta.id)
        )
        return list(self._sessao.scalars(consulta))

    def listar_todos(self) -> list[Alerta]:
        return list(self._sessao.scalars(select(Alerta).order_by(Alerta.id)))

    def obter_por_url(self, url: str) -> Alerta | None:
        return self._sessao.scalars(select(Alerta).where(Alerta.url == url)).one_or_none()

    def adicionar(self, alerta: Alerta) -> None:
        self._sessao.add(alerta)
