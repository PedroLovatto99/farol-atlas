"""A rodada real não coleta sem um contato de verdade no User-Agent (princípio IV)."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from pydantic import SecretStr

from farol.infra import ClienteEducado, Configuracoes
from farol.worker import (
    CONTATO_DE_EXEMPLO,
    ContatoInvalido,
    rodada_real,
    rodada_real_de_postos,
    rodada_real_de_vistos,
)
from farol.worker import jobs as modulo_de_jobs


def configuracao(contato: str | None) -> Configuracoes:
    return Configuracoes(
        database_url=SecretStr("postgresql+psycopg://x:y@banco-que-nao-existe/z"),
        contato_coleta=contato,
    )


@pytest.mark.parametrize("contato", [None, "", "   ", CONTATO_DE_EXEMPLO])
def test_sem_contato_de_verdade_a_coleta_nem_comeca(contato: str | None) -> None:
    # o erro vem antes de qualquer acesso ao banco ou à rede
    with pytest.raises(ContatoInvalido, match="CONTATO_COLETA"):
        rodada_real(configuracao(contato))


@pytest.mark.parametrize("contato", [None, "", "   ", CONTATO_DE_EXEMPLO])
def test_sem_contato_de_verdade_a_coleta_de_postos_nem_comeca(contato: str | None) -> None:
    with pytest.raises(ContatoInvalido, match="CONTATO_COLETA"):
        rodada_real_de_postos(configuracao(contato))


# --------------------------------------------------------------------------- vistos
@pytest.mark.parametrize("contato", [None, "", "   ", CONTATO_DE_EXEMPLO])
def test_sem_contato_de_verdade_a_coleta_de_vistos_nem_comeca(contato: str | None) -> None:
    with pytest.raises(ContatoInvalido, match="CONTATO_COLETA"):
        rodada_real_de_vistos(configuracao(contato))


class ServicoDeVistosFalso:
    """Guarda o que a rodada real lhe entregou e devolve um resumo qualquer."""

    criados: list["ServicoDeVistosFalso"] = []  # noqa: RUF012

    def __init__(self, sessao: object, cliente: object, relogio: object, tradutor: object) -> None:
        self.sessao, self.cliente, self.relogio, self.tradutor = sessao, cliente, relogio, tradutor
        self.agendada: bool | None = None
        ServicoDeVistosFalso.criados.append(self)

    def coletar(self, *, agendada: bool = False) -> str:
        self.agendada = agendada
        return "resumo"


@pytest.fixture
def servico_falso(monkeypatch: pytest.MonkeyPatch) -> type[ServicoDeVistosFalso]:
    ServicoDeVistosFalso.criados = []

    @contextmanager
    def sessao_falsa() -> Iterator[str]:
        yield "sessao"

    monkeypatch.setattr(modulo_de_jobs, "abrir_sessao", sessao_falsa)
    monkeypatch.setattr(modulo_de_jobs, "ServicoDeColetaDeVistos", ServicoDeVistosFalso)
    return ServicoDeVistosFalso


def test_a_rodada_de_vistos_usa_o_cliente_educado_com_o_contato_e_a_pausa(
    servico_falso: type[ServicoDeVistosFalso], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_de_jobs, "criar_tradutor", lambda _: "tradutor")
    configuracoes = configuracao("https://github.com/dono/farol")
    configuracoes.pausa_segundos = 3.5

    resumo: Any = rodada_real_de_vistos(configuracoes)

    assert resumo == "resumo"
    [servico] = servico_falso.criados
    assert isinstance(servico.cliente, ClienteEducado)
    assert "https://github.com/dono/farol" in servico.cliente.user_agent
    assert servico.cliente._pausa == 3.5
    assert servico.sessao == "sessao"
    assert servico.tradutor == "tradutor"


def test_a_rodada_de_vistos_nao_e_agendada_por_padrao(
    servico_falso: type[ServicoDeVistosFalso], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_de_jobs, "criar_tradutor", lambda _: "tradutor")
    rodada_real_de_vistos(configuracao("https://github.com/dono/farol"))
    assert servico_falso.criados[0].agendada is False


def test_a_rodada_agendada_liga_o_aviso_de_pendencias(
    servico_falso: type[ServicoDeVistosFalso], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(modulo_de_jobs, "criar_tradutor", lambda _: "tradutor")
    rodada_real_de_vistos(configuracao("https://github.com/dono/farol"), agendada=True)
    assert servico_falso.criados[0].agendada is True


def test_sem_llm_a_coleta_de_vistos_segue_com_o_tradutor_ausente(
    servico_falso: type[ServicoDeVistosFalso],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def sem_modelo(_: Configuracoes) -> object:
        raise ValueError("sem chave do provedor")

    monkeypatch.setattr(modulo_de_jobs, "criar_tradutor", sem_modelo)
    with caplog.at_level(logging.ERROR, logger="farol.worker"):
        resumo: Any = rodada_real_de_vistos(configuracao("https://github.com/dono/farol"))

    assert resumo == "resumo"  # a coleta não parou
    assert servico_falso.criados[0].tradutor is None
    assert any("tradutor indisponível" in r.getMessage() for r in caplog.records)


def test_modelo_que_nao_existe_tambem_deixa_o_tradutor_ausente(
    servico_falso: type[ServicoDeVistosFalso],
) -> None:
    # sem simulação: o `init_chat_model` de verdade recusa um provedor desconhecido
    configuracoes = configuracao("https://github.com/dono/farol")
    configuracoes.llm_tradutor = "provedor_que_nao_existe:modelo"
    rodada_real_de_vistos(configuracoes)
    assert servico_falso.criados[0].tradutor is None
