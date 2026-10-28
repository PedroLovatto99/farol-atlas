"""Fixtures dos testes de unidade de `vistos`: a página real, lida uma vez, e os dicionários."""

from pathlib import Path

import pytest

from farol.dominio.seed import carregar
from farol.vistos.dicionario import Dicionario, carregar_dicionario
from farol.vistos.fonte import LinhaDaFonte, extrair_linhas

DADOS = Path(__file__).resolve().parents[4] / "dados"
AREAS_NEUTRAS = frozenset({"EH", "AQ"})  # Saara Ocidental e Antártida (observacoes.yaml)


@pytest.fixture(scope="session")
def linhas_da_fonte(html_da_wikipedia: str) -> list[LinhaDaFonte]:
    """As 249 linhas das três tabelas da fixture."""
    return extrair_linhas(html_da_wikipedia)


@pytest.fixture(scope="session")
def codigos_do_mapa() -> frozenset[str]:
    """Códigos de países e dependências semeados em `territorio` (as áreas neutras não entram)."""
    dados = carregar(DADOS)
    return frozenset(dados.nomes_dos_paises) | {d["codigo"] for d in dados.dependencias}


@pytest.fixture(scope="session")
def dicionario_real(codigos_do_mapa: frozenset[str]) -> Dicionario:
    """Os três arquivos reais, validados contra o seed (código existente e não neutro)."""
    return carregar_dicionario(codigos_validos=codigos_do_mapa, codigos_neutros=AREAS_NEUTRAS)
