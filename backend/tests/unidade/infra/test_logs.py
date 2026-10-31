"""Logs: JSON na saída padrão e, se pedido, num arquivo rotativo que sobrevive ao contêiner."""

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from farol.infra import configurar_logs, obter_logger
from farol.infra.logs import COPIAS_DO_ARQUIVO, TAMANHO_MAXIMO_DO_ARQUIVO


@pytest.fixture(autouse=True)
def restaurar_log_raiz() -> Iterator[None]:
    raiz = logging.getLogger()
    antes, nivel = list(raiz.handlers), raiz.level
    yield
    for manipulador in raiz.handlers:
        if manipulador not in antes:
            manipulador.close()
    raiz.handlers, raiz.level = antes, nivel


def test_sem_diretorio_so_ha_a_saida_padrao() -> None:
    configurar_logs()
    nomes = [type(m).__name__ for m in logging.getLogger().handlers]
    assert nomes == ["StreamHandler"]


def test_com_diretorio_grava_json_no_arquivo(tmp_path: Path) -> None:
    configurar_logs(diretorio=tmp_path / "logs")  # a pasta é criada se não existir
    obter_logger("farol.teste").info("rodada concluída")
    for manipulador in logging.getLogger().handlers:
        manipulador.flush()
    linhas = (tmp_path / "logs" / "worker.log").read_text(encoding="utf-8").splitlines()
    evento = json.loads(linhas[-1])
    assert evento["mensagem"] == "rodada concluída"
    assert evento["logger"] == "farol.teste"


def test_o_arquivo_gira_e_guarda_poucas_copias(tmp_path: Path) -> None:
    configurar_logs(diretorio=tmp_path)
    manipulador = next(
        m
        for m in logging.getLogger().handlers
        if isinstance(m, logging.handlers.RotatingFileHandler)
    )
    assert manipulador.maxBytes == TAMANHO_MAXIMO_DO_ARQUIVO
    assert manipulador.backupCount == COPIAS_DO_ARQUIVO


def test_reconfigurar_nao_duplica_manipuladores(tmp_path: Path) -> None:
    configurar_logs(diretorio=tmp_path)
    configurar_logs(diretorio=tmp_path)
    assert len(logging.getLogger().handlers) == 2


def test_arquivo_novo_continua_o_antigo_depois_de_recriar_o_conteiner(tmp_path: Path) -> None:
    """O volume guarda o arquivo: um processo novo acrescenta, não apaga."""
    configurar_logs(diretorio=tmp_path)
    obter_logger("farol.teste").info("antes")
    configurar_logs(diretorio=tmp_path)  # o "contêiner novo"
    obter_logger("farol.teste").info("depois")
    for manipulador in logging.getLogger().handlers:
        manipulador.flush()
    texto = (tmp_path / "worker.log").read_text(encoding="utf-8")
    assert "antes" in texto
    assert "depois" in texto
