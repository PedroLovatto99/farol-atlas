"""Permanência (FR-004a): só formatos conhecidos são padronizados; o resto fica como a fonte."""

import pytest

from farol.vistos.fonte import (
    TABELA_DE_TERRITORIOS,
    TABELA_NAO_RECONHECIDOS,
    TABELA_PRINCIPAL,
    extrair_linhas,
)
from farol.vistos.permanencia import Permanencia, TipoDePermanencia, ler_permanencia


@pytest.mark.parametrize(
    ("fonte", "esperado"),
    [
        ("90 days", "90 dias"),
        ("1 day", "1 dia"),
        ("1 days", "1 dia"),
        ("2 weeks", "2 semanas"),
        ("6 weeks", "6 semanas"),
        ("1 week", "1 semana"),
        ("3 months", "3 meses"),
        ("1 month", "1 mês"),
        ("6 months", "6 meses"),
        ("1 year", "1 ano"),
        ("2 years", "2 anos"),
        ("1 YEAR", "1 ano"),
        ("30 Days", "30 dias"),
    ],
)
def test_formatos_simples_sao_padronizados(fonte: str, esperado: str) -> None:
    resultado = ler_permanencia(fonte)
    assert resultado == Permanencia(TipoDePermanencia.PADRONIZADA, esperado)


@pytest.mark.parametrize(
    ("fonte", "esperado"),
    [
        ("90 days in any 180-day period", "90 dias a cada período de 180 dias"),
        ("1 day in any 2-day period", "1 dia a cada período de 2 dias"),
        ("30 days in any 60 day period", "30 dias a cada período de 60 dias"),
    ],
)
def test_periodo_deslizante_e_padronizado(fonte: str, esperado: str) -> None:
    assert ler_permanencia(fonte) == Permanencia(TipoDePermanencia.PADRONIZADA, esperado)


def test_meses_nao_viram_dias() -> None:
    resultado = ler_permanencia("3 months")
    assert resultado.texto == "3 meses"
    assert "90" not in (resultado.texto or "")


@pytest.mark.parametrize(
    "fonte",
    [
        "up to 90 days",
        "14 days / 30 days",
        "30 days / 60 days",
        "90 days within any 180-day period",
        "Unlimited",
        "30 days, extendable to 180 days",
        "90 days (business), 6 months (tourist)",
    ],
)
def test_outros_formatos_ficam_como_na_fonte_em_ingles(fonte: str) -> None:
    assert ler_permanencia(fonte) == Permanencia(TipoDePermanencia.ORIGINAL, fonte)


@pytest.mark.parametrize("fonte", ["", "   ", "\xa0"])
def test_coluna_em_branco_nao_tem_permanencia(fonte: str) -> None:
    assert ler_permanencia(fonte) == Permanencia(TipoDePermanencia.NENHUMA, None)


def test_espacos_e_caixa_na_fonte_sao_tolerados() -> None:
    assert ler_permanencia("  90   days ") == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")


def test_o_modulo_nao_usa_tradutor() -> None:
    import ast
    import inspect

    from farol.vistos import permanencia

    arvore = ast.parse(inspect.getsource(permanencia))
    importados = {n.module or "" for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names
    }
    assert not any("tradutor" in nome or "langchain" in nome for nome in importados)


def test_na_fixture_so_a_tabela_principal_tem_permanencia(html_da_wikipedia: str) -> None:
    """O3: das tabelas de territórios o prazo não é lido; só vale a coluna "Allowed stay"."""
    linhas = extrair_linhas(html_da_wikipedia)
    principal = [lin for lin in linhas if lin.tabela == TABELA_PRINCIPAL]
    outras = [
        lin for lin in linhas if lin.tabela in (TABELA_NAO_RECONHECIDOS, TABELA_DE_TERRITORIOS)
    ]

    tipos = [ler_permanencia(lin.permanencia).tipo for lin in principal]
    assert tipos.count(TipoDePermanencia.NENHUMA) == 40
    assert tipos.count(TipoDePermanencia.PADRONIZADA) == 150
    assert tipos.count(TipoDePermanencia.ORIGINAL) == 3
    assert all(ler_permanencia(lin.permanencia).tipo is TipoDePermanencia.NENHUMA for lin in outras)

    por_nome = {lin.nome: ler_permanencia(lin.permanencia) for lin in principal}
    assert por_nome["Ethiopia"] == Permanencia(TipoDePermanencia.ORIGINAL, "up to 90 days")
    assert por_nome["Oman"] == Permanencia(TipoDePermanencia.ORIGINAL, "14 days / 30 days")
    assert por_nome["Tajikistan"] == Permanencia(TipoDePermanencia.ORIGINAL, "30 days / 60 days")
    assert por_nome["Guyana"] == Permanencia(TipoDePermanencia.PADRONIZADA, "3 meses")
    assert por_nome["Albania"] == Permanencia(TipoDePermanencia.PADRONIZADA, "90 dias")
