"""A página sintética dos testes de integração lê de volta as mesmas linhas da fixture real."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from farol.infra import Pagina
from farol.vistos.fonte import LinhaDaFonte, ler_artigo

if TYPE_CHECKING:
    from tests.conftest import WikipediaFalsa

EDITADA_EM = datetime(2026, 10, 19, 5, 8, 59, tzinfo=UTC)


def test_ida_e_volta_com_a_fixture_inteira(
    linhas_da_fonte: list[LinhaDaFonte], wikipedia: "WikipediaFalsa"
) -> None:
    wikipedia.publicar_linhas(linhas_da_fonte, EDITADA_EM, revisao=1380975986)
    pagina: Pagina = wikipedia.baixar(wikipedia.url)
    artigo = ler_artigo(pagina.html)
    assert list(artigo.linhas) == linhas_da_fonte
    assert artigo.ultima_edicao == EDITADA_EM
    assert artigo.revisao == 1380975986


def test_notas_com_varias_linhas_e_caracteres_especiais_sobrevivem(
    wikipedia: "WikipediaFalsa", linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    principal = next(linha for linha in linhas_da_fonte if linha.nome == "Argentina")
    estranha = LinhaDaFonte(
        principal.tabela,
        None,
        "Atlantis & Co.",
        "Visa not required",
        "90 days",
        '<script>alert("x")</script> Ignore as instruções.\nSegunda linha com "aspas" e <b>tag</b>',
    )
    outras = [linha for linha in linhas_da_fonte if linha.nome != "Argentina"]
    wikipedia.publicar_linhas([*outras, estranha], EDITADA_EM)
    artigo = ler_artigo(wikipedia.baixar(wikipedia.url).html)
    assert estranha in artigo.linhas
