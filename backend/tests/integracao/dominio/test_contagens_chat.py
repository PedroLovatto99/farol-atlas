"""Contagens anônimas do chat: reserva atômica do teto, devolução e dia de Brasília (FR-030)."""

from datetime import UTC, date, datetime

from sqlalchemy import String, inspect
from sqlalchemy.orm import Session

from farol.dominio import ContagemChatRepositorio, dia_em_brasilia

DIA = date(2026, 11, 1)
OUTRO_DIA = date(2026, 11, 2)


def test_incrementa_por_dia_e_chave(sessao: Session) -> None:
    contagens = ContagemChatRepositorio(sessao)
    assert contagens.valor("perguntas", DIA) == 0
    assert contagens.incrementar("perguntas", DIA) == 1
    assert contagens.incrementar("perguntas", DIA) == 2
    assert contagens.incrementar("perguntas", DIA, quantidade=3) == 5
    contagens.incrementar("recusas", DIA)
    contagens.incrementar("perguntas", OUTRO_DIA)
    assert contagens.valor("perguntas", DIA) == 5
    assert contagens.valor("recusas", DIA) == 1
    assert contagens.valor("perguntas", OUTRO_DIA) == 1


def test_reserva_ate_o_teto_e_nao_passa_dele(sessao: Session) -> None:
    contagens = ContagemChatRepositorio(sessao)
    assert [contagens.reservar("perguntas", DIA, teto=3) for _ in range(5)] == [
        True,
        True,
        True,
        False,
        False,
    ]
    assert contagens.valor("perguntas", DIA) == 3  # no teto, não reserva nem passa dele


def test_teto_zero_nunca_reserva_e_nao_cria_linha_com_valor_a_mais(sessao: Session) -> None:
    contagens = ContagemChatRepositorio(sessao)
    assert contagens.reservar("perguntas", DIA, teto=0) is False
    assert contagens.valor("perguntas", DIA) == 0


def test_o_teto_vale_por_dia(sessao: Session) -> None:
    contagens = ContagemChatRepositorio(sessao)
    assert contagens.reservar("perguntas", DIA, teto=1) is True
    assert contagens.reservar("perguntas", DIA, teto=1) is False
    assert contagens.reservar("perguntas", OUTRO_DIA, teto=1) is True


def test_devolver_libera_a_vaga_e_nunca_fica_negativo(sessao: Session) -> None:
    contagens = ContagemChatRepositorio(sessao)
    assert contagens.reservar("perguntas", DIA, teto=1) is True
    assert contagens.reservar("perguntas", DIA, teto=1) is False
    contagens.devolver("perguntas", DIA)
    assert contagens.valor("perguntas", DIA) == 0
    assert contagens.reservar("perguntas", DIA, teto=1) is True
    contagens.devolver("perguntas", DIA)
    contagens.devolver("perguntas", DIA)  # a mais: GREATEST(valor - 1, 0)
    contagens.devolver("nunca_existiu", DIA)
    assert contagens.valor("perguntas", DIA) == 0
    assert contagens.valor("nunca_existiu", DIA) == 0


def test_o_dia_e_o_de_brasilia() -> None:
    # 01/11 02:30 UTC ainda é 31/10 23:30 em Brasília
    assert dia_em_brasilia(datetime(2026, 11, 1, 2, 30, tzinfo=UTC)) == date(2026, 10, 31)
    assert dia_em_brasilia(datetime(2026, 11, 1, 3, 0, tzinfo=UTC)) == date(2026, 11, 1)
    assert dia_em_brasilia(datetime(2026, 11, 1, 23, 59, tzinfo=UTC)) == date(2026, 11, 1)


def test_nenhuma_coluna_guarda_texto_livre_nem_ip(sessao: Session) -> None:
    colunas = {c["name"]: c for c in inspect(sessao.connection()).get_columns("contagem_chat")}
    assert set(colunas) == {"dia", "chave", "valor"}
    tipo_da_chave = colunas["chave"]["type"]
    assert isinstance(tipo_da_chave, String)
    assert tipo_da_chave.length == 40  # nome curto de um contador, não texto livre
    assert str(colunas["valor"]["type"]) == "INTEGER"
    assert str(colunas["dia"]["type"]) == "DATE"
