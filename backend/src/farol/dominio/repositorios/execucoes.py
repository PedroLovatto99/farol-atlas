"""Gravação e consulta das execuções de coleta."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio.enums import TipoExecucao
from farol.dominio.modelos import ExecucaoColeta


class ExecucaoRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def ultima_completa(self, tipo: TipoExecucao) -> ExecucaoColeta | None:
        """A última coleta completa: é dela que vêm os níveis exibidos (FR-040)."""
        consulta = (
            select(ExecucaoColeta)
            .where(
                ExecucaoColeta.tipo == tipo,
                ExecucaoColeta.completa.is_(True),
                ExecucaoColeta.finalizada_em.is_not(None),
            )
            .order_by(ExecucaoColeta.finalizada_em.desc(), ExecucaoColeta.id.desc())
            .limit(1)
        )
        return self._sessao.scalars(consulta).first()

    def ultima_tentativa(self, tipo: TipoExecucao) -> ExecucaoColeta | None:
        consulta = (
            select(ExecucaoColeta)
            .where(ExecucaoColeta.tipo == tipo)
            .order_by(ExecucaoColeta.iniciada_em.desc(), ExecucaoColeta.id.desc())
            .limit(1)
        )
        return self._sessao.scalars(consulta).first()

    def adicionar(self, execucao: ExecucaoColeta) -> None:
        self._sessao.add(execucao)
