"""O índice acompanha os alertas: o que é novo entra, o que mudou ou saiu deixa de valer.

A coleta completa e a classificação vêm antes; a primeira passada do varredor depois delas põe o
alerta no índice (a cada 5 minutos, dentro dos 15 de FR-008). Enquanto isso, a consulta já esconde o
que saiu da lista ou mudou de conteúdo, e a resposta nunca mistura versões (SC-015).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from tests.falsos_chat import (
    AGORA,
    EmbeddadorFalso,
    RelogioFixo,
    execucao_completa,
    gravar_alerta,
    hash_do_texto,
    semear_territorios,
)

from farol.chat import RecuperadorDeTrechos, indexar_pendentes
from farol.dominio import Alerta, Classificacao, NivelAlerta, NivelTerritorio
from farol.infra import Configuracoes
from farol.mapa import alertas_que_definem_nivel

ANTIGO = "As fronteiras da Bolívia estão fechadas por tempo indeterminado devido aos bloqueios."
NOVO = "As fronteiras da Bolívia foram reabertas e a circulação nas rodovias foi restabelecida."
EVITAR_BO = [{"territorio": "BO", "nivel_pais": "evitar", "regioes": []}]
URL = "postgresql+psycopg://farol:farol@postgres:5432/farol"
PERGUNTA = "fronteiras da Bolívia"


def _passada(sessao: Session, embeddador: EmbeddadorFalso) -> None:
    indexar_pendentes(
        sessao,
        embeddador,
        alertas_que_definem_nivel(sessao),
        modelo=embeddador.modelo,
        dimensoes=embeddador.dimensoes,
        relogio=RelogioFixo(),
    )


def _achados(sessao: Session, embeddador: EmbeddadorFalso) -> list[tuple[str, bool]]:
    """`(texto do trecho, em vigor)` de tudo o que a pergunta traz para a Bolívia, anteriores
    incluídos (o que se confere aqui é o vigor gravado no índice)."""
    recuperador = RecuperadorDeTrechos(
        sessao, embeddador, modelo=embeddador.modelo, dimensoes=embeddador.dimensoes
    )
    saida = []
    for a in recuperador.recuperar(PERGUNTA, paises=["BO"], so_em_vigor=False):
        alerta = sessao.get(Alerta, a.alerta_id)
        assert alerta is not None and alerta.texto is not None
        saida.append((alerta.texto[a.inicio : a.fim], a.em_vigor))
    return saida


@pytest.fixture
def embeddador() -> EmbeddadorFalso:
    return EmbeddadorFalso()


def test_alerta_novo_so_aparece_depois_da_primeira_passada(
    sessao: Session, embeddador: EmbeddadorFalso
) -> None:
    semear_territorios(sessao)
    gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url="https://x/novo",
        titulo="Bolívia",
        texto=NOVO,
        niveis=EVITAR_BO,
    )
    assert _achados(sessao, embeddador) == []

    _passada(sessao, embeddador)  # uma passada só

    assert _achados(sessao, embeddador) == [(NOVO, True)]


def test_alerta_alterado_nunca_mistura_o_conteudo_antigo_com_o_novo(
    sessao: Session, embeddador: EmbeddadorFalso
) -> None:
    semear_territorios(sessao)
    alerta = gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url="https://x/a",
        titulo="Bolívia",
        texto=ANTIGO,
        niveis=EVITAR_BO,
    )
    _passada(sessao, embeddador)
    assert [t for t, _ in _achados(sessao, embeddador)] == [ANTIGO]

    # a coleta completa confirma o conteúdo novo e o classificador o classifica
    alerta.texto = NOVO
    alerta.html_corpo = None
    alerta.hash = alerta.confirmado_hash = hash_do_texto(NOVO)
    nova = Classificacao(
        alerta_id=alerta.id,
        alerta_hash=alerta.hash,
        status=alerta.classificacoes[0].status,
        e_alerta_de_viagem=True,
        modelo="falso",
        classificado_em=AGORA,
    )
    sessao.add(nova)
    sessao.flush()
    sessao.add(
        NivelTerritorio(
            classificacao_id=nova.id, territorio_codigo="BO", nivel_pais=NivelAlerta.EVITAR
        )
    )
    sessao.flush()

    # antes da passada: o conteúdo antigo já não é devolvido (e o novo ainda não está no índice)
    assert _achados(sessao, embeddador) == []

    _passada(sessao, embeddador)

    textos = [t for t, _ in _achados(sessao, embeddador)]
    assert textos == [NOVO]
    assert not any("fechadas" in t for t in textos)


def test_alerta_substituido_vira_anterior_e_o_novo_passa_a_reger(
    sessao: Session, embeddador: EmbeddadorFalso
) -> None:
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    gravar_alerta(
        sessao,
        execucao,
        url="https://x/velho",
        titulo="Bolívia, bloqueios",
        texto=ANTIGO,
        publicado_em=AGORA - timedelta(days=10),
        niveis=EVITAR_BO,
    )
    _passada(sessao, embeddador)
    assert _achados(sessao, embeddador) == [(ANTIGO, True)]

    gravar_alerta(
        sessao,
        execucao,
        url="https://x/novo",
        titulo="Bolívia, normalizada",
        texto=NOVO,
        publicado_em=AGORA,
        niveis=[{"territorio": "BO", "nivel_pais": "normalizada", "regioes": []}],
    )
    _passada(sessao, embeddador)  # o `vigor` agora vem do alerta novo; o antigo não é reembedado

    assert dict(_achados(sessao, embeddador)) == {ANTIGO: False, NOVO: True}


def test_alerta_removido_deixa_de_ser_orientacao_antes_mesmo_da_passada(
    sessao: Session, embeddador: EmbeddadorFalso
) -> None:
    semear_territorios(sessao)
    alerta = gravar_alerta(
        sessao,
        execucao_completa(sessao),
        url="https://x/a",
        titulo="Bolívia",
        texto=ANTIGO,
        niveis=EVITAR_BO,
    )
    _passada(sessao, embeddador)
    assert _achados(sessao, embeddador)

    alerta.removido_em = datetime(2026, 11, 1, tzinfo=UTC)
    sessao.flush()

    assert _achados(sessao, embeddador) == []
    _passada(sessao, embeddador)
    assert _achados(sessao, embeddador) == []


def test_o_intervalo_padrao_da_varredura_cabe_nos_15_minutos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INDEXACAO_INTERVALO_MINUTOS", raising=False)
    padrao = Configuracoes(_env_file=None, database_url=URL).indexacao_intervalo_minutos
    # pior caso: o alerta fica pronto logo depois de uma passada e espera a seguinte
    assert padrao * 2 <= 15
