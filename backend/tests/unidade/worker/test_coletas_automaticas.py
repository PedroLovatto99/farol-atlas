"""COLETAS_AUTOMATICAS: desligada, o worker fica de pé sem agendar nem coletar nada."""

from typing import Any

import pytest
from pydantic import SecretStr

from farol.infra import Configuracoes
from farol.worker import agendador_ocioso, comando


class AgendadorFalso:
    def __init__(self) -> None:
        self.iniciado = False

    def start(self) -> None:
        self.iniciado = True


def _configuracoes(**campos: Any) -> Configuracoes:
    return Configuracoes(database_url=SecretStr("postgresql+psycopg://x:y@nao-existe/z"), **campos)


def test_agendador_ocioso_nao_tem_jobs() -> None:
    assert agendador_ocioso().get_jobs() == []


def test_desligadas_o_worker_sobe_sem_tocar_no_banco_nem_agendar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agendador = AgendadorFalso()
    monkeypatch.setattr(comando, "obter_configuracoes", lambda: _configuracoes())
    monkeypatch.setattr(comando, "agendador_ocioso", lambda: agendador)

    def sem_banco(*_: object) -> None:
        raise AssertionError("o worker ocioso não deve abrir o banco")

    monkeypatch.setattr(comando, "abrir_sessao", sem_banco)
    monkeypatch.setattr(comando, "preparar_agendador", sem_banco)

    comando.servir_agenda()

    assert agendador.iniciado


def test_ligadas_o_worker_monta_a_agenda_de_sempre(monkeypatch: pytest.MonkeyPatch) -> None:
    chamadas: list[str] = []

    class SessaoFalsa:
        def __enter__(self) -> object:
            chamadas.append("banco")
            raise RuntimeError("parou aqui")

        def __exit__(self, *_: object) -> None: ...

    monkeypatch.setattr(
        comando, "obter_configuracoes", lambda: _configuracoes(coletas_automaticas=True)
    )
    monkeypatch.setattr(comando, "abrir_sessao", lambda: SessaoFalsa())
    monkeypatch.setattr(
        comando, "agendador_ocioso", lambda: pytest.fail("não era para ficar ocioso")
    )

    with pytest.raises(RuntimeError, match="parou aqui"):
        comando.servir_agenda()

    assert chamadas == ["banco"]


# --------------------------------------------------------------------------- indexação (003)
def _servir(monkeypatch: pytest.MonkeyPatch, **campos: Any) -> dict[str, Any]:
    """Roda `servir_agenda` com tudo trocado e devolve o que `preparar_agendador` recebeu."""
    recebido: dict[str, Any] = {}

    class SessaoFalsa:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *_: object) -> None: ...

    class ExecucoesFalsas:
        def __init__(self, _sessao: object) -> None: ...

        def ultima_tentativa(self, _tipo: object) -> None:
            return None

    def preparar(rodada: object, **kwargs: Any) -> AgendadorFalso:
        recebido.update(kwargs)
        return AgendadorFalso()

    monkeypatch.setattr(
        comando,
        "obter_configuracoes",
        lambda: _configuracoes(coletas_automaticas=True, **campos),
    )
    monkeypatch.setattr(comando, "abrir_sessao", lambda: SessaoFalsa())
    monkeypatch.setattr(comando, "ExecucaoRepositorio", ExecucoesFalsas)
    monkeypatch.setattr(
        comando,
        "situacao_de_vistos_na_partida",
        lambda _sessao: comando.SituacaoDeVistosNaPartida(None, False, None),
    )
    monkeypatch.setattr(comando, "preparar_agendador", preparar)
    comando.servir_agenda()
    return recebido


def test_com_o_chat_pronto_o_worker_agenda_a_indexacao(monkeypatch: pytest.MonkeyPatch) -> None:
    recebido = _servir(
        monkeypatch,
        chat_habilitado=True,
        google_api_key_chat=SecretStr("chave-do-chat"),
        indexacao_intervalo_minutos=7,
    )

    assert callable(recebido["rodada_de_indexacao"])
    assert recebido["intervalo_da_indexacao_minutos"] == 7


def test_com_o_chat_desligado_o_worker_nao_agenda_a_indexacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recebido = _servir(monkeypatch, chat_habilitado=False)
    assert recebido.get("rodada_de_indexacao") is None


def test_chat_ligado_sem_a_chave_do_chat_nao_agenda_a_indexacao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recebido = _servir(monkeypatch, chat_habilitado=True)
    assert recebido.get("rodada_de_indexacao") is None
