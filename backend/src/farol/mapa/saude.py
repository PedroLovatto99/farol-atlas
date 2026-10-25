"""Estado de saúde do sistema: banco e coleta (usado por GET /saude)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from farol.dominio import (
    BancoRepositorio,
    ClassificacaoRepositorio,
    ExecucaoRepositorio,
    TipoExecucao,
)


@dataclass(frozen=True)
class EstadoDeSaude:
    banco_ok: bool
    ultima_coleta_completa_em: datetime | None
    ultima_tentativa_em: datetime | None
    alertas_pendentes: int


def consultar_saude(sessao: Session) -> EstadoDeSaude:
    if not BancoRepositorio(sessao).responde():
        return EstadoDeSaude(False, None, None, 0)
    execucoes = ExecucaoRepositorio(sessao)
    completa = execucoes.ultima_completa(TipoExecucao.ALERTAS)
    tentativa = execucoes.ultima_tentativa(TipoExecucao.ALERTAS)
    return EstadoDeSaude(
        banco_ok=True,
        ultima_coleta_completa_em=completa.finalizada_em if completa else None,
        ultima_tentativa_em=tentativa.iniciada_em if tentativa else None,
        alertas_pendentes=ClassificacaoRepositorio(sessao).contar_alertas_pendentes(),
    )
