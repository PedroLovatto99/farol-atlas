"""Trechos do chat acompanham a classificação: o que apagar e o que refazer (prazo de 15 min).

Fluxos que mexem na classificação: `reclassificar` (grava na MESMA linha, só avança
`classificado_em`) e a coleta com conteúdo novo (cria outra linha, para o novo hash). Nenhum
fluxo apaga a linha, mas, se alguém a apagar, os trechos vão junto (CASCADE).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from farol.dominio import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    StatusClassificacao,
    TipoExecucao,
    TrechoAlerta,
    TrechoAlertaRepositorio,
)

AGORA = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
HASH = "a" * 64
MODELO = "google_genai:gemini-embedding-001"


def _alerta(sessao: Session, url: str = "https://gov.br/t1", hash_: str = HASH) -> Alerta:
    execucao = ExecucaoColeta(tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA, completa=True)
    sessao.add(execucao)
    sessao.flush()
    registro = Alerta(
        url=url,
        titulo="Alerta",
        texto="Texto do alerta para o índice de trechos.",
        hash=hash_,
        confirmado_execucao_id=execucao.id,
        confirmado_hash=hash_,
        publicado_em=AGORA,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
    )
    sessao.add(registro)
    sessao.flush()
    return registro


def _classificar(sessao: Session, alerta: Alerta, hash_: str = HASH) -> Classificacao:
    classificacao = Classificacao(
        alerta_id=alerta.id,
        alerta_hash=hash_,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=True,
        modelo="falso",
        classificado_em=AGORA,
    )
    sessao.add(classificacao)
    sessao.flush()
    return classificacao


def _indexar(
    sessao: Session,
    alerta: Alerta,
    classificacao: Classificacao,
    *,
    indexado_em: datetime = AGORA,
    hash_: str = HASH,
    modelo: str = MODELO,
) -> None:
    sessao.add(
        TrechoAlerta(
            alerta_id=alerta.id,
            alerta_hash=hash_,
            classificacao_id=classificacao.id,
            posicao=0,
            inicio=0,
            fim=10,
            paises=["BO"],
            em_vigor_para=[],
            modelo_embedding=modelo,
            dimensoes=3,
            embedding=[0.1, 0.2, 0.3],
            indexado_em=indexado_em,
        )
    )
    sessao.flush()


def _a_indexar(sessao: Session) -> list[int]:
    return TrechoAlertaRepositorio(sessao).alertas_a_indexar(MODELO, 3)


def test_apagar_a_classificacao_apaga_os_trechos_e_o_alerta_volta_a_pendente(
    sessao: Session,
) -> None:
    alerta = _alerta(sessao)
    classificacao = _classificar(sessao, alerta)
    _indexar(sessao, alerta, classificacao)
    assert _a_indexar(sessao) == []

    sessao.execute(text("delete from classificacao where id = :id"), {"id": classificacao.id})

    assert sessao.execute(text("select count(*) from trecho_alerta")).scalar_one() == 0
    assert _a_indexar(sessao) == []  # sem classificação ok, não há o que indexar


def test_alerta_classificado_sem_trechos_esta_a_indexar(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _classificar(sessao, alerta)
    assert _a_indexar(sessao) == [alerta.id]


def test_trechos_em_dia_nao_precisam_de_reindexacao(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _indexar(sessao, alerta, _classificar(sessao, alerta))
    assert _a_indexar(sessao) == []


def test_classificacao_refeita_na_mesma_linha_deixa_os_trechos_defasados(
    sessao: Session,
) -> None:
    """É o que `reclassificar` faz: mesmo id e hash, `classificado_em` novo."""
    alerta = _alerta(sessao)
    classificacao = _classificar(sessao, alerta)
    _indexar(sessao, alerta, classificacao)

    classificacao.classificado_em = AGORA + timedelta(minutes=1)
    sessao.flush()

    assert _a_indexar(sessao) == [alerta.id]


def test_conteudo_novo_pede_indexacao_e_o_trecho_antigo_nao_conta(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _indexar(sessao, alerta, _classificar(sessao, alerta))
    novo = "b" * 64
    alerta.confirmado_hash = novo
    _classificar(sessao, alerta, novo)
    sessao.flush()

    assert _a_indexar(sessao) == [alerta.id]


def test_trechos_de_outro_modelo_ou_dimensao_nao_contam(sessao: Session) -> None:
    alerta = _alerta(sessao)
    _indexar(sessao, alerta, _classificar(sessao, alerta), modelo="outro:modelo")
    assert _a_indexar(sessao) == [alerta.id]
    assert TrechoAlertaRepositorio(sessao).alertas_a_indexar("outro:modelo", 3) == []
    assert TrechoAlertaRepositorio(sessao).alertas_a_indexar("outro:modelo", 4) == [alerta.id]


def test_alerta_removido_ou_sem_classificacao_ok_nao_entra(sessao: Session) -> None:
    removido = _alerta(sessao, "https://gov.br/t2")
    _classificar(sessao, removido)
    removido.removido_em = AGORA
    falhou = _alerta(sessao, "https://gov.br/t3")
    _classificar(sessao, falhou).status = StatusClassificacao.FALHOU
    sessao.flush()
    assert _a_indexar(sessao) == []
