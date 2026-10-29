"""Detector de verificação humana: desafio real é detectado; a palavra solta em script, não.

O detector descarta só o texto entre as tags de `<script>` e `<style>`; atributos (`src`,
`class`, `id`, `data-*`) e o texto visível continuam examinados.
"""

import pytest

from farol.infra import parece_verificacao


def pagina(corpo: str) -> str:
    return f"<html><head><title>Página</title></head><body>{corpo}</body></html>"


@pytest.mark.parametrize(
    "corpo",
    [
        '<iframe src="https://www.google.com/recaptcha/api2/anchor?k=chave"></iframe>',
        '<div class="g-recaptcha" data-sitekey="chave"></div>',
        '<div class="h-captcha" data-sitekey="chave"></div>',
        '<script src="https://exemplo.gov.br/static/captcha.js"></script>',
        "<p>Please wait while we are testing whether you are a human</p>",
        "<p>This is needed to prevent automated spam</p>",
        '<div data-desafio="captcha"></div>',
    ],
    ids=[
        "iframe-recaptcha",
        "div-g-recaptcha",
        "div-h-captcha",
        "script-por-atributo",
        "frase-testing-human",
        "frase-automated-spam",
        "atributo-data",
    ],
)
def test_desafio_real_continua_detectado(corpo: str) -> None:
    assert parece_verificacao(pagina(corpo))


def test_frases_sao_detectadas_sem_diferenciar_maiusculas() -> None:
    assert parece_verificacao(pagina("<p>TESTING WHETHER YOU ARE A HUMAN</p>"))


@pytest.mark.parametrize(
    "corpo",
    [
        '<script>mw.config.set({"wgConfirmEditCaptchaNeededForGenericEdit":"hcaptcha"});</script>',
        '<script type="application/json">{"chave":"captcha"}</script>',
        "<style>.captcha { display: none; }</style>",
        "<script>\nvar a = 1;\n// captcha\n</script>",
        "<SCRIPT>captcha</SCRIPT>",
    ],
    ids=["script-inline", "script-json", "style", "script-multilinha", "maiusculas"],
)
def test_palavra_so_dentro_de_script_ou_style_nao_e_verificacao(corpo: str) -> None:
    assert not parece_verificacao(pagina(corpo))


def test_texto_fora_do_script_continua_examinado_ao_lado_de_um_script() -> None:
    corpo = "<script>var a = 1;</script><p>testing whether you are a human</p>"
    assert parece_verificacao(pagina(corpo))


def test_script_inline_nao_esconde_o_atributo_de_outra_tag() -> None:
    corpo = '<script>var a = 1;</script><div class="h-captcha"></div>'
    assert parece_verificacao(pagina(corpo))


def test_pagina_comum_nao_e_verificacao() -> None:
    assert not parece_verificacao(pagina("<p>conteúdo real</p>"))
