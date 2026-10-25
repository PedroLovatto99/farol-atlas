"""Observações das dependências (dados/territorios/observacoes.yaml), sem precisar de banco."""

from pathlib import Path

import pytest

from farol.dominio.seed import DadosSeed, ErroDeSeed, carregar, observacao_da_dependencia

RAIZ = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def dados() -> DadosSeed:
    return carregar(RAIZ / "dados")


@pytest.mark.parametrize(
    ("codigo", "soberano", "inicio"),
    [
        ("GL", "DK", "Território da Dinamarca."),
        ("PR", "US", "Território dos Estados Unidos."),
        ("VG", "GB", "Território do Reino Unido."),
        ("AW", "NL", "Território dos Países Baixos."),
        ("NC", "FR", "Território da França."),
        ("NF", "AU", "Território da Austrália."),
        ("CK", "NZ", "Território da Nova Zelândia."),
        ("AX", "FI", "Território da Finlândia."),
    ],
)
def test_observacao_padrao_usa_a_preposicao_do_soberano(
    dados: DadosSeed, codigo: str, soberano: str, inicio: str
) -> None:
    observacao = observacao_da_dependencia(codigo, soberano, dados)
    assert observacao.startswith(inicio)
    assert "salvo um alerta específico mais recente" in observacao


@pytest.mark.parametrize("codigo", ["HK", "MO"])
def test_hong_kong_e_macau_sao_regioes_administrativas_especiais(
    dados: DadosSeed, codigo: str
) -> None:
    observacao = observacao_da_dependencia(codigo, "CN", dados)
    assert observacao.startswith("Região administrativa especial da China.")


def test_todo_soberano_de_dependencia_tem_a_forma_com_preposicao(dados: DadosSeed) -> None:
    for dependencia in dados.dependencias:
        observacao = observacao_da_dependencia(
            dependencia["codigo"], dependencia["soberano_codigo"], dados
        )
        assert "{" not in observacao, dependencia["codigo"]
        assert " de Estados Unidos" not in observacao
        assert " de Países Baixos" not in observacao
        assert " de Reino Unido" not in observacao


def test_soberano_sem_forma_com_preposicao_falha_de_forma_ruidosa(dados: DadosSeed) -> None:
    with pytest.raises(ErroDeSeed, match="XX"):
        observacao_da_dependencia("ZZ", "XX", dados)


def test_busca_da_ilha_christmas_e_das_ilhas_cocos(dados: DadosSeed) -> None:
    especial = dados.observacoes["territorios"]["IOA"]
    assert {"Christmas", "Cocos"} <= set(especial["termos_busca"])
