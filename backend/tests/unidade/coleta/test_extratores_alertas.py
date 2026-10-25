"""Extratores da lista de alertas e da página de cada alerta, sobre as fixtures reais do gov.br."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from farol.coleta import ErroDeExtracao, extrair_alerta, extrair_lista_de_alertas

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "govbr"
URL_DA_LISTA = (
    "https://www.gov.br/mre/pt-br/assuntos/portal-consular/alertas%20e%20noticias/alertas"
)


def ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def bloco(titulo: str, caminho: str, data: str) -> str:
    return (
        '<div class="listagem-noticias-com-foto"><div class="conteudo">'
        f'<h2 class="titulo"><a href="{caminho}">{titulo}</a></h2>'
        f'<span class="descricao"><span class="data">{data}</span></span></div></div>'
    )


# --------------------------------------------------------------------------- lista
def test_lista_real_tem_18_itens_e_nenhuma_proxima_pagina() -> None:
    lista = extrair_lista_de_alertas(ler("lista_alertas.html"), URL_DA_LISTA)
    assert len(lista.itens) == 18
    assert lista.proxima_pagina is None


def test_primeiro_item_da_lista() -> None:
    [primeiro, *_] = extrair_lista_de_alertas(ler("lista_alertas.html"), URL_DA_LISTA).itens
    assert primeiro.titulo == "Alerta de viagem – Bolívia"
    assert primeiro.url == f"{URL_DA_LISTA}/alerta-de-viagem-2013-bolivia"
    # a lista só traz a data: meia-noite em São Paulo (UTC-3)
    assert primeiro.publicado_em == datetime(2026, 7, 10, 3, 0, tzinfo=UTC)


def test_links_relativos_viram_absolutos() -> None:
    html = bloco("Alerta X", "/mre/pt-br/alerta-x", "01/02/2026")
    [item] = extrair_lista_de_alertas(html, URL_DA_LISTA).itens
    assert item.url == "https://www.gov.br/mre/pt-br/alerta-x"


def test_item_sem_link_e_ignorado() -> None:
    html = (
        '<div class="listagem-noticias-com-foto"><div class="conteudo">'
        '<h2 class="titulo">sem link</h2><span class="data">01/02/2026</span></div></div>'
    )
    assert extrair_lista_de_alertas(html, URL_DA_LISTA).itens == ()


def test_item_com_data_invalida_e_ignorado() -> None:
    html = bloco("Alerta X", "/mre/alerta-x", "ontem")
    assert extrair_lista_de_alertas(html, URL_DA_LISTA).itens == ()


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><body><p>Manutenção programada</p></body></html>",
        '<div class="listagem-noticias-com-foto"></div>',
    ],
    ids=["vazia", "formato-inesperado", "lista-sem-itens"],
)
def test_lista_sem_nenhum_item_vem_vazia(html: str) -> None:
    lista = extrair_lista_de_alertas(html, URL_DA_LISTA)
    assert lista.itens == ()  # o serviço trata como lista incompleta
    assert lista.proxima_pagina is None


@pytest.mark.parametrize(
    "link",
    [
        '<a href="?b_start:int=20" class="next">Próximo</a>',
        '<a href="?b_start%3Aint=20">Próxima página</a>',
        '<a rel="next" href="?b_start:int=20">2</a>',
    ],
    ids=["classe-next", "rotulo-proxima", "rel-next"],
)
def test_reconhece_o_link_de_proxima_pagina(link: str) -> None:
    html = bloco("Alerta X", "/mre/alerta-x", "01/02/2026") + f"<nav>{link}</nav>"
    lista = extrair_lista_de_alertas(html, URL_DA_LISTA)
    assert lista.proxima_pagina is not None
    assert lista.proxima_pagina.startswith(URL_DA_LISTA)
    assert "b_start" in lista.proxima_pagina
    assert len(lista.itens) == 1


def test_link_de_pagina_anterior_nao_e_proxima_pagina() -> None:
    html = bloco("Alerta X", "/mre/alerta-x", "01/02/2026") + (
        '<nav><a href="?b_start:int=0" class="previous">Anterior</a></nav>'
    )
    assert extrair_lista_de_alertas(html, URL_DA_LISTA).proxima_pagina is None


def test_link_qualquer_com_a_palavra_proximo_nao_e_paginacao() -> None:
    html = bloco("Alerta X", "/mre/alerta-x", "01/02/2026") + (
        '<nav><a href="/mre/agenda">Próximos eventos</a></nav>'
    )
    assert extrair_lista_de_alertas(html, URL_DA_LISTA).proxima_pagina is None


# --------------------------------------------------------------------------- alerta
def test_alerta_1_bolivia() -> None:
    alerta = extrair_alerta(ler("alerta_1.html"))
    assert alerta.titulo == "Alerta de viagem – Bolívia"
    assert alerta.categoria == "Brasileiro indo para o exterior"
    assert alerta.publicado_em == datetime(2026, 7, 10, 19, 35, 55, tzinfo=UTC)
    assert alerta.modificado_em == datetime(2026, 7, 10, 19, 35, 55, tzinfo=UTC)
    assert alerta.texto.startswith(
        "O Ministério das Relações Exteriores informa que foi restabelecida"
    )
    assert "  " not in alerta.texto  # espaços colapsados
    assert "\n" not in alerta.texto


def test_alerta_2_foi_modificado_depois_de_publicado() -> None:
    alerta = extrair_alerta(ler("alerta_2.html"))
    assert alerta.titulo == "Alerta Consular. Oriente Médio."
    assert alerta.publicado_em == datetime(2026, 7, 4, 16, 10, tzinfo=UTC)
    assert alerta.modificado_em == datetime(2026, 8, 17, 19, 23, 16, tzinfo=UTC)
    assert "Sul do Líbano" in alerta.texto


def test_alerta_3_e_de_apoio_a_cidadaos() -> None:
    alerta = extrair_alerta(ler("alerta_3.html"))
    assert alerta.categoria == "Apoio a Cidadãos"
    assert alerta.publicado_em == datetime(2026, 6, 15, 22, 18, 12, tzinfo=UTC)


def test_html_do_corpo_fica_guardado_para_reprocessar() -> None:
    alerta = extrair_alerta(ler("alerta_1.html"))
    assert alerta.html_corpo.startswith("<div")
    assert "<p>" in alerta.html_corpo


def test_sem_json_ld_usa_o_publicado_em_da_pagina() -> None:
    sem_json_ld = re.sub(
        r'<script type="application/ld\+json">.*?</script>', "", ler("alerta_1.html"), flags=re.S
    )
    alerta = extrair_alerta(sem_json_ld)
    # "Publicado em 10/07/2026 16h35" (horário de Brasília), sem data de modificação
    assert alerta.publicado_em == datetime(2026, 7, 10, 19, 35, tzinfo=UTC)
    assert alerta.modificado_em is None


@pytest.mark.parametrize(
    "html",
    ["", "<html><body><p>Nada aqui</p></body></html>"],
    ids=["vazia", "formato-inesperado"],
)
def test_pagina_em_formato_inesperado_levanta_erro(html: str) -> None:
    with pytest.raises(ErroDeExtracao):
        extrair_alerta(html)


def test_alerta_sem_data_levanta_erro() -> None:
    sem_datas = re.sub(
        r'<script type="application/ld\+json">.*?</script>', "", ler("alerta_1.html"), flags=re.S
    )
    sem_datas = sem_datas.replace("documentPublished", "outraCoisa")
    with pytest.raises(ErroDeExtracao, match="data"):
        extrair_alerta(sem_datas)
