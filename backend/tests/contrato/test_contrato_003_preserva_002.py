"""Trava: o contrato da 003 preserva tudo o que o da 002 já prometia.

Usa a mesma trava da 002 sobre a 001 (`violacoes`): nenhuma rota, operação, parâmetro, resposta ou
esquema da 002 pode sumir ou mudar, e nenhuma propriedade nova entra num esquema antigo. A 003 só
acrescenta a rota `POST /chat` e esquemas novos.
"""

import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from tests.contrato.test_contrato_002_preserva_001 import violacoes

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

RAIZ_SPECS = Path(__file__).resolve().parents[3] / "specs"
CONTRATO_002 = RAIZ_SPECS / "002-visto-brasileiros" / "contracts" / "openapi.yaml"
CONTRATO_003 = RAIZ_SPECS / "003-chat-alertas-viagem" / "contracts" / "openapi.yaml"


@pytest.fixture(scope="module")
def contrato_002() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO_002.read_text(encoding="utf-8"))
    return carregado


@pytest.fixture(scope="module")
def contrato_003() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO_003.read_text(encoding="utf-8"))
    return carregado


def test_a_003_preserva_tudo_o_que_a_002_prometia(
    contrato_002: Documento, contrato_003: Documento, normalizacao: "Normalizacao"
) -> None:
    assert violacoes(contrato_002, contrato_003, normalizacao.esboco, aprovadas={}) == []


def test_a_unica_rota_nova_e_o_post_do_chat(
    contrato_002: Documento, contrato_003: Documento
) -> None:
    assert set(contrato_003["paths"]) - set(contrato_002["paths"]) == {"/chat"}
    assert set(contrato_003["paths"]["/chat"]) == {"post"}
    for caminho, rota in contrato_002["paths"].items():
        assert set(contrato_003["paths"][caminho]) == set(rota) == {"get"}, caminho


def test_a_trava_aponta_uma_mudanca_na_parte_da_002(
    contrato_002: Documento, contrato_003: Documento, normalizacao: "Normalizacao"
) -> None:
    alterado = copy.deepcopy(contrato_003)
    alterado["components"]["schemas"]["Visto"]["properties"]["novidade"] = {"type": "string"}
    assert violacoes(contrato_002, alterado, normalizacao.esboco, aprovadas={}) == [
        "propriedade nova fora da lista aprovada: Visto.novidade"
    ]
