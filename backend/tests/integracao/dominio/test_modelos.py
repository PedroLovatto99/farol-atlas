"""Modelos e restrições do banco (data-model.md)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from farol.dominio.enums import (
    NivelAlerta,
    StatusClassificacao,
    TipoExecucao,
    TipoPosto,
    TipoTerritorio,
)
from farol.dominio.modelos import (
    Alerta,
    Classificacao,
    ExecucaoColeta,
    NivelTerritorio,
    Posto,
    Territorio,
)

AGORA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
HASH = "a" * 64


def pais(codigo: str = "DK", nome: str = "Dinamarca") -> Territorio:
    return Territorio(codigo=codigo, nome_pt=nome, tipo=TipoTerritorio.PAIS)


def posto(**campos: object) -> Posto:
    base: dict[str, object] = {
        "id": 1,
        "territorio_codigo": "DK",
        "cidade": "Copenhague",
        "tipo": TipoPosto.EMBAIXADA,
        "latitude": Decimal("55.67610"),
        "longitude": Decimal("12.56830"),
    }
    base.update(campos)
    return Posto(**base)


def alerta(url: str = "https://gov.br/a1") -> Alerta:
    return Alerta(
        url=url,
        titulo="Alerta de viagem – Bolívia",
        publicado_em=AGORA,
        primeira_coleta_em=AGORA,
        ultima_coleta_em=AGORA,
    )


def test_dependencia_exige_soberano(sessao: Session) -> None:
    sessao.add(
        Territorio(codigo="GL", nome_pt="Groenlândia (Dinamarca)", tipo=TipoTerritorio.DEPENDENCIA)
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_dependencia_com_soberano_e_aceita(sessao: Session) -> None:
    sessao.add(pais())
    sessao.flush()
    sessao.add(
        Territorio(
            codigo="GL",
            nome_pt="Groenlândia (Dinamarca)",
            tipo=TipoTerritorio.DEPENDENCIA,
            soberano_codigo="DK",
        )
    )
    sessao.flush()


def test_endereco_exige_fonte_e_data_da_coleta(sessao: Session) -> None:
    sessao.add(pais())
    sessao.flush()
    sessao.add(posto(endereco="Botanisk Have 1"))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_telefone_exige_fonte_e_data_da_coleta(sessao: Session) -> None:
    sessao.add(pais())
    sessao.flush()
    sessao.add(posto(telefone_plantao="+45 1234 5678", contato_coletado_em=AGORA))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_posto_com_contato_completo_e_aceito(sessao: Session) -> None:
    sessao.add(pais())
    sessao.flush()
    sessao.add(
        posto(
            endereco="Botanisk Have 1",
            telefone_plantao="+45 1234 5678",
            contato_coletado_em=AGORA,
            contato_fonte_url="https://www.gov.br/mre/pt-br/embaixada-copenhague",
        )
    )
    sessao.flush()


def test_posto_sem_contato_e_aceito(sessao: Session) -> None:
    sessao.add(pais())
    sessao.flush()
    sessao.add(posto())
    sessao.flush()


def test_url_do_alerta_e_unica(sessao: Session) -> None:
    sessao.add(alerta())
    sessao.flush()
    sessao.add(alerta())
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_uma_classificacao_por_alerta_e_hash(sessao: Session) -> None:
    a = alerta()
    sessao.add(a)
    sessao.flush()
    for _ in range(2):
        sessao.add(
            Classificacao(
                alerta_id=a.id,
                alerta_hash=HASH,
                status=StatusClassificacao.OK,
                e_alerta_de_viagem=True,
                modelo="modelo-falso",
                classificado_em=AGORA,
            )
        )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_nivel_territorio_nao_repete_territorio_na_classificacao(sessao: Session) -> None:
    sessao.add(pais("BO", "Bolívia"))
    a = alerta()
    sessao.add(a)
    sessao.flush()
    c = Classificacao(
        alerta_id=a.id,
        alerta_hash=HASH,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=True,
        modelo="modelo-falso",
        classificado_em=AGORA,
    )
    sessao.add(c)
    sessao.flush()
    sessao.add(
        NivelTerritorio(
            classificacao_id=c.id, territorio_codigo="BO", nivel_pais=NivelAlerta.NORMALIZADA
        )
    )
    sessao.flush()
    sessao.add(
        NivelTerritorio(
            classificacao_id=c.id, territorio_codigo="BO", nivel_pais=NivelAlerta.EVITAR
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_nivel_territorio_guarda_regioes(sessao: Session) -> None:
    sessao.add(pais("LB", "Líbano"))
    a = alerta()
    sessao.add(a)
    sessao.flush()
    c = Classificacao(
        alerta_id=a.id,
        alerta_hash=HASH,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=True,
        modelo="modelo-falso",
        classificado_em=AGORA,
    )
    sessao.add(c)
    sessao.flush()
    sessao.add(
        NivelTerritorio(
            classificacao_id=c.id,
            territorio_codigo="LB",
            nivel_pais=NivelAlerta.EVITAR,
            regioes=[{"nome": "Sul do Líbano", "nivel": "nao_viajar"}],
        )
    )
    sessao.flush()
    sessao.expire_all()
    item = sessao.get(NivelTerritorio, (c.id, "LB"))
    assert item is not None
    assert item.regioes == [{"nome": "Sul do Líbano", "nivel": "nao_viajar"}]


def test_execucao_de_coleta_tem_valores_padrao(sessao: Session) -> None:
    execucao = ExecucaoColeta(tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA)
    sessao.add(execucao)
    sessao.flush()
    assert execucao.completa is False
    assert execucao.paginas_esperadas == 0
    assert execucao.paginas_lidas == 0
