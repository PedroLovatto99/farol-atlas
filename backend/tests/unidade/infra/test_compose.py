"""Garante as regras do docker-compose.yml de desenvolvimento (constituição, princípio VIII)."""

from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[4]
BANCOS = ["postgres", "postgres-teste"]
PORTA_DO_POSTGRES = "5432"  # porta dentro do container; a do host pode ser trocada pelo .env


@pytest.fixture(scope="module")
def servicos() -> dict[str, dict[str, Any]]:
    conteudo = yaml.safe_load((RAIZ / "docker-compose.yml").read_text(encoding="utf-8"))
    servicos: dict[str, dict[str, Any]] = conteudo["services"]
    return servicos


def _portas(servico: dict[str, Any]) -> list[str]:
    return [str(porta) for porta in servico.get("ports", [])]


@pytest.mark.parametrize("nome", BANCOS)
def test_banco_publica_porta_so_no_loopback(servicos: dict[str, dict[str, Any]], nome: str) -> None:
    portas = _portas(servicos[nome])
    assert portas, f"{nome} deveria publicar a porta do banco em 127.0.0.1"
    for publicada in portas:
        assert publicada.startswith("127.0.0.1:"), (
            f"{nome} publica {publicada!r}; bancos só podem ligar em 127.0.0.1"
        )
        assert publicada.endswith(f":{PORTA_DO_POSTGRES}")


def test_nenhum_outro_servico_publica_porta_de_banco(servicos: dict[str, dict[str, Any]]) -> None:
    for nome, servico in servicos.items():
        if nome in BANCOS:
            continue
        for publicada in _portas(servico):
            destino = publicada.split(":")[-1].split("/")[0]
            assert destino not in {"5432", "5433"}, f"{nome} publica a porta de banco {publicada}"


def test_api_e_worker_usam_a_mesma_imagem(servicos: dict[str, dict[str, Any]]) -> None:
    assert servicos["api"]["image"] == servicos["worker"]["image"]


@pytest.mark.parametrize("nome", ["api", "worker"])
def test_servicos_esperam_a_migracao_terminar(
    servicos: dict[str, dict[str, Any]], nome: str
) -> None:
    dependencias = servicos[nome]["depends_on"]
    assert dependencias["migracao"]["condition"] == "service_completed_successfully"
