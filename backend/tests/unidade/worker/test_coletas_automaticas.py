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
