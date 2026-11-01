"""`alertas_que_definem_nivel`: para cada alerta, os territórios cujo nível ele rege (o `vigor`).

É o mesmo "quem rege" do painel (`define_nivel`) e do mapa (`calcular_niveis`); o worker entrega o
resultado ao chat, que não importa o `mapa`.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session
from tests.falsos_chat import AGORA, execucao_completa, gravar_alerta, semear_territorios

from farol.mapa import alertas_que_definem_nivel, montar_painel


def _niveis(*pares: tuple[str, str]) -> list[dict[str, Any]]:
    return [{"territorio": codigo, "nivel_pais": nivel, "regioes": []} for codigo, nivel in pares]


def test_sem_coleta_completa_ninguem_rege_nada(sessao: Session) -> None:
    semear_territorios(sessao)
    assert alertas_que_definem_nivel(sessao) == {}


def test_o_alerta_mais_recente_rege_e_o_anterior_nao_aparece(sessao: Session) -> None:
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    antigo = gravar_alerta(
        sessao,
        execucao,
        url="https://x/1",
        titulo="Antigo",
        texto="a",
        publicado_em=AGORA - timedelta(days=9),
        niveis=_niveis(("BO", "evitar")),
    )
    novo = gravar_alerta(
        sessao,
        execucao,
        url="https://x/2",
        titulo="Novo",
        texto="b",
        publicado_em=AGORA,
        niveis=_niveis(("BO", "nao_viajar"), ("PE", "evitar")),
    )

    vigor = alertas_que_definem_nivel(sessao)

    assert vigor == {novo.id: frozenset({"BO", "PE"})}
    assert antigo.id not in vigor


def test_alerta_que_nao_e_de_viagem_ou_removido_nao_rege(sessao: Session) -> None:
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    gravar_alerta(
        sessao, execucao, url="https://x/1", titulo="Fraude", texto="a", e_alerta_de_viagem=False
    )
    removido = gravar_alerta(
        sessao,
        execucao,
        url="https://x/2",
        titulo="Removido",
        texto="b",
        niveis=_niveis(("BO", "evitar")),
    )
    removido.removido_em = datetime(2026, 11, 1, tzinfo=UTC)
    sessao.flush()

    assert alertas_que_definem_nivel(sessao) == {}


def test_bate_com_o_alerta_que_o_painel_marca_como_regente(sessao: Session) -> None:
    semear_territorios(sessao)
    execucao = execucao_completa(sessao)
    gravar_alerta(
        sessao,
        execucao,
        url="https://x/1",
        titulo="Oriente",
        texto="a",
        publicado_em=AGORA - timedelta(days=3),
        niveis=_niveis(("IL", "nao_viajar")),
    )
    recente = gravar_alerta(
        sessao,
        execucao,
        url="https://x/2",
        titulo="Israel de novo",
        texto="b",
        publicado_em=AGORA,
        niveis=_niveis(("IL", "evitar"), ("JO", "evitar")),
    )

    vigor = alertas_que_definem_nivel(sessao)

    for codigo in ("IL", "JO", "BO"):
        regentes = {a.url for a in montar_painel(sessao, codigo).alertas if a.define_nivel}
        quem_diz = {recente.url for codigos in vigor.values() if codigo in codigos}
        assert quem_diz == regentes
    assert vigor == {recente.id: frozenset({"IL", "JO"})}
