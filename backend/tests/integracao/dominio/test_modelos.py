"""Modelos e restrições do banco (data-model.md)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
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
    ContagemChat,
    ExecucaoColeta,
    NivelTerritorio,
    Posto,
    Territorio,
    TrechoAlerta,
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


# --------------------------------------------------------------------------- chat (003)
def _alerta_classificado(sessao: Session, url: str = "https://gov.br/chat1") -> tuple[Alerta, int]:
    """Um alerta com hash confirmado e a classificação vigente dele (a base de um trecho)."""
    registro = alerta(url)
    registro.texto = "Texto do alerta para o índice de trechos."
    registro.confirmado_hash = HASH
    sessao.add(registro)
    sessao.flush()
    classificacao = Classificacao(
        alerta_id=registro.id,
        alerta_hash=HASH,
        status=StatusClassificacao.OK,
        e_alerta_de_viagem=True,
        modelo="falso",
        classificado_em=AGORA,
    )
    sessao.add(classificacao)
    sessao.flush()
    return registro, classificacao.id


def _trecho(registro: Alerta, classificacao_id: int, **campos: object) -> TrechoAlerta:
    base: dict[str, object] = {
        "alerta_id": registro.id,
        "alerta_hash": HASH,
        "classificacao_id": classificacao_id,
        "posicao": 0,
        "inicio": 0,
        "fim": 10,
        "paises": ["BO"],
        "em_vigor_para": [],
        "modelo_embedding": "google_genai:gemini-embedding-001",
        "dimensoes": 3,
        "embedding": [0.1, 0.2, 0.3],
        "indexado_em": AGORA,
    }
    base.update(campos)
    return TrechoAlerta(**base)


def test_trecho_unico_por_alerta_hash_modelo_dimensao_e_posicao(sessao: Session) -> None:
    registro, classificacao_id = _alerta_classificado(sessao)
    sessao.add(_trecho(registro, classificacao_id))
    sessao.flush()
    sessao.add(_trecho(registro, classificacao_id))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_dois_modelos_de_dimensoes_diferentes_coexistem(sessao: Session) -> None:
    registro, classificacao_id = _alerta_classificado(sessao)
    sessao.add_all(
        [
            _trecho(registro, classificacao_id),
            _trecho(
                registro,
                classificacao_id,
                modelo_embedding="outro:modelo",
                dimensoes=4,
                embedding=[0.1, 0.2, 0.3, 0.4],
            ),
        ]
    )
    sessao.flush()
    total = sessao.execute(text("select count(*) from trecho_alerta")).scalar_one()
    assert total == 2


@pytest.mark.parametrize(
    "campos",
    [
        {"inicio": 5, "fim": 5},
        {"inicio": 8, "fim": 3},
        {"dimensoes": 0},
        {"dimensoes": -3},
        {"dimensoes": 4},  # o vetor tem 3
    ],
    ids=["fim-igual", "fim-menor", "dimensao-zero", "dimensao-negativa", "vetor-diferente"],
)
def test_trecho_recusa_intervalo_e_dimensao_invalidos(
    sessao: Session, campos: dict[str, object]
) -> None:
    registro, classificacao_id = _alerta_classificado(sessao)
    sessao.add(_trecho(registro, classificacao_id, **campos))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_apagar_o_alerta_apaga_os_trechos(sessao: Session) -> None:
    registro, classificacao_id = _alerta_classificado(sessao)
    sessao.add(_trecho(registro, classificacao_id))
    sessao.flush()
    chaves = list(inspect(sessao.connection()).get_foreign_keys("trecho_alerta"))
    do_alerta = next(fk for fk in chaves if fk["constrained_columns"] == ["alerta_id"])
    assert do_alerta["options"]["ondelete"] == "CASCADE"
    # a classificação do alerta também referencia o alerta; some junto, na mesma instrução
    sessao.execute(
        text(
            "with c as (delete from classificacao where alerta_id = :id) "
            "delete from alerta where id = :id"
        ),
        {"id": registro.id},
    )
    assert sessao.execute(text("select count(*) from trecho_alerta")).scalar_one() == 0


def test_contagem_chat_tem_chave_dia_e_chave_e_valor_nao_negativo(sessao: Session) -> None:
    dia = AGORA.date()
    sessao.add(ContagemChat(dia=dia, chave="perguntas", valor=3))
    sessao.add(ContagemChat(dia=dia, chave="recusas"))  # valor padrão 0
    sessao.flush()
    assert sessao.get_one(ContagemChat, (dia, "recusas")).valor == 0
    sessao.add(ContagemChat(dia=dia, chave="perguntas", valor=1))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_contagem_chat_recusa_valor_negativo(sessao: Session) -> None:
    sessao.add(ContagemChat(dia=AGORA.date(), chave="perguntas", valor=-1))
    with pytest.raises(IntegrityError):
        sessao.flush()
