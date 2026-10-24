"""Leitura e gravação de alertas, com suas classificações."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from farol.dominio.enums import StatusClassificacao
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

    def listar_para_classificar(self) -> list[Alerta]:
        """Alertas ativos, com a página lida, sem classificação `ok` para o hash atual.

        Inclui os que falharam antes (a próxima rodada tenta de novo) e os lidos numa coleta
        incompleta (a classificação já fica pronta quando uma coleta completa os confirmar).
        """
        classificado = (
            select(Classificacao.id)
            .where(
                Classificacao.alerta_id == Alerta.id,
                Classificacao.alerta_hash == Alerta.hash,
                Classificacao.status == StatusClassificacao.OK,
            )
            .exists()
        )
        consulta = (
            select(Alerta)
            .where(
                Alerta.pagina_lida.is_(True),
                Alerta.hash.is_not(None),
                Alerta.removido_em.is_(None),
                ~classificado,
            )
            .order_by(Alerta.id)
        )
        return list(self._sessao.scalars(consulta))

    def listar_todos(self) -> list[Alerta]:
        return list(self._sessao.scalars(select(Alerta).order_by(Alerta.id)))

    def obter_por_url(self, url: str) -> Alerta | None:
        return self._sessao.scalars(select(Alerta).where(Alerta.url == url)).one_or_none()

    def adicionar(self, alerta: Alerta) -> None:
        self._sessao.add(alerta)
