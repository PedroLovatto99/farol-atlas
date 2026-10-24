"""Guarda da fonte dos postos: os CSVs não mudam sem o fonte.yaml ser atualizado.

A linha "Postos: Itamaraty e Wikipédia (CC BY-SA), conferidos em ..." do painel vem do fonte.yaml
(FR-011a). Se alguém atualizar os CSVs e esquecer o fonte.yaml, a data exibida ficaria errada.
"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from farol.dominio.seed import hash_do_arquivo

POSTOS = Path(__file__).resolve().parents[4] / "dados" / "postos"
CSVS = ("postos_brasileiros.csv", "jurisdicao_cumulativa.csv")


@pytest.fixture(scope="module")
def fonte() -> dict[str, Any]:
    conteudo: dict[str, Any] = yaml.safe_load((POSTOS / "fonte.yaml").read_text(encoding="utf-8"))
    return conteudo


def test_fonte_yaml_tem_data_e_fontes_com_nome_e_url(fonte: dict[str, Any]) -> None:
    assert fonte["chave"] == "postos"
    assert isinstance(fonte["conferido_em"], date)
    assert fonte["fontes"], "o fonte.yaml precisa citar ao menos uma fonte"
    for item in fonte["fontes"]:
        assert item["nome"]
        assert item["url"].startswith("https://")


def test_wikipedia_vem_com_a_licenca_cc_by_sa(fonte: dict[str, Any]) -> None:
    [wikipedia] = [f for f in fonte["fontes"] if f["nome"].startswith("Wikipédia")]
    assert wikipedia["licenca"] == "CC BY-SA"


@pytest.mark.parametrize("arquivo", CSVS)
def test_hash_dos_csvs_bate_com_o_fonte_yaml(fonte: dict[str, Any], arquivo: str) -> None:
    registrado = fonte["arquivos"][arquivo]
    atual = hash_do_arquivo(POSTOS / arquivo)
    assert registrado == atual, (
        f"{arquivo} mudou sem o dados/postos/fonte.yaml ser atualizado. Atualize `conferido_em` "
        "(data em que os dados foram conferidos) e o hash em `arquivos`.\n"
        "Para ver os hashes atuais: uv run python -m farol.dominio.seed --hashes"
    )
