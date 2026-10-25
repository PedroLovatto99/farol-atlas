"""Gravação e consulta de classificações."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from farol.dominio.enums import StatusClassificacao
from farol.dominio.modelos import Alerta, Classificacao


class ClassificacaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def obter(self, alerta_id: int, alerta_hash: str) -> Classificacao | None:
        consulta = select(Classificacao).where(
            Classificacao.alerta_id == alerta_id, Classificacao.alerta_hash == alerta_hash
        )
        return self._sessao.scalars(consulta).one_or_none()

    def adicionar(self, classificacao: Classificacao) -> None:
        self._sessao.add(classificacao)

    def contar_alertas_pendentes(self) -> int:
        """Alertas confirmados e ativos sem classificação `ok` para o conteúdo confirmado."""
        classificado = (
            select(Classificacao.id)
            .where(
                Classificacao.alerta_id == Alerta.id,
                Classificacao.alerta_hash == Alerta.confirmado_hash,
                Classificacao.status == StatusClassificacao.OK,
            )
            .exists()
        )
        consulta = select(func.count(Alerta.id)).where(
            Alerta.confirmado_execucao_id.is_not(None),
            Alerta.removido_em.is_(None),
            ~classificado,
        )
        return self._sessao.scalar(consulta) or 0
