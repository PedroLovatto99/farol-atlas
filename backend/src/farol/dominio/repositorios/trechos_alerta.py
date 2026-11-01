"""Consulta do índice de trechos dos alertas (o que falta indexar)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.dominio.enums import StatusClassificacao
from farol.dominio.modelos import Alerta, Classificacao, TrechoAlerta


class TrechoAlertaRepositorio:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def alertas_a_indexar(self, modelo_embedding: str, dimensoes: int) -> list[int]:
        """Ids dos alertas confirmados, ativos e com classificação `ok` do conteúdo confirmado
        que não têm trechos em dia: nenhum, ou de outro conteúdo (hash), de outra classificação, de
        uma classificação refeita depois da indexação ou de outro modelo ou dimensão."""
        em_dia = (
            select(TrechoAlerta.id)
            .where(
                TrechoAlerta.alerta_id == Alerta.id,
                TrechoAlerta.alerta_hash == Alerta.confirmado_hash,
                TrechoAlerta.classificacao_id == Classificacao.id,
                TrechoAlerta.indexado_em >= Classificacao.classificado_em,
                TrechoAlerta.modelo_embedding == modelo_embedding,
                TrechoAlerta.dimensoes == dimensoes,
            )
            .exists()
        )
        consulta = (
            select(Alerta.id)
            .join(
                Classificacao,
                (Classificacao.alerta_id == Alerta.id)
                & (Classificacao.alerta_hash == Alerta.confirmado_hash)
                & (Classificacao.status == StatusClassificacao.OK),
            )
            .where(
                Alerta.confirmado_execucao_id.is_not(None),
                Alerta.removido_em.is_(None),
                Alerta.pagina_lida.is_(True),
                ~em_dia,
            )
            .order_by(Alerta.id)
        )
        return list(self._sessao.scalars(consulta))
