"""A página real da Wikipédia não pode ser tomada por verificação humana.

A palavra "captcha" aparece nela só no texto inline de `<script>` (configuração do MediaWiki).
"""

from pathlib import Path

from bs4 import BeautifulSoup

from farol.infra import parece_verificacao

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "wikipedia"
    / "visa_requirements_for_brazilian_citizens.html"
)


def test_a_fixture_da_wikipedia_nao_e_verificacao_humana() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    assert not parece_verificacao(html)


def test_a_palavra_captcha_existe_na_fixture_so_dentro_de_script() -> None:
    """Trava para o teste acima não ficar vazio: a palavra existe, mas só em `<script>`."""
    html = FIXTURE.read_text(encoding="utf-8")
    total = html.lower().count("captcha")
    assert total == 4

    sopa = BeautifulSoup(html, "html.parser")
    em_scripts = sum(
        (script.string or script.get_text()).lower().count("captcha")
        for script in sopa.find_all("script")
    )
    assert em_scripts == total
