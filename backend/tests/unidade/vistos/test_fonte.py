"""Extração da página do artigo da Wikipédia (sem rede: a fixture é a página real)."""

from collections import Counter
from datetime import UTC, datetime

import pytest

from farol.vistos.fonte import (
    LICENCA_DA_FONTE,
    NOME_DA_FONTE,
    TABELA_DE_TERRITORIOS,
    TABELA_NAO_RECONHECIDOS,
    TABELA_PRINCIPAL,
    URL_DO_ARTIGO,
    ErroDeFormato,
    extrair_edicao,
    extrair_linhas,
    ler_artigo,
)


def test_identificacao_da_fonte() -> None:
    assert URL_DO_ARTIGO == "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens"
    assert "Wikipedia" in NOME_DA_FONTE or "Wikipédia" in NOME_DA_FONTE
    assert LICENCA_DA_FONTE == "CC BY-SA"


# --------------------------------------------------------------------------- data da edição
def test_data_da_edicao_vem_do_json_ld_e_a_revisao_do_script(html_da_wikipedia: str) -> None:
    edicao = extrair_edicao(html_da_wikipedia)
    assert edicao.ultima_edicao == datetime(2026, 10, 19, 5, 8, 59, tzinfo=UTC)
    assert edicao.revisao == 1380975986


def test_sem_json_ld_a_data_vem_do_rodape(html_da_wikipedia: str) -> None:
    sem_json_ld = html_da_wikipedia.replace('"dateModified"', '"outraCoisa"')
    edicao = extrair_edicao(sem_json_ld)
    assert edicao.ultima_edicao == datetime(2026, 10, 19, 5, 8, tzinfo=UTC)
    assert edicao.revisao == 1380975986


def test_json_ld_com_data_invalida_cai_no_rodape(html_da_wikipedia: str) -> None:
    html = html_da_wikipedia.replace("2026-10-19T05:08:59Z", "ontem")
    assert extrair_edicao(html).ultima_edicao == datetime(2026, 10, 19, 5, 8, tzinfo=UTC)


def test_sem_json_ld_e_sem_rodape_e_erro_de_formato(html_da_wikipedia: str) -> None:
    html = html_da_wikipedia.replace('"dateModified"', '"outraCoisa"').replace(
        "This page was last edited on", "Esta pagina foi editada em"
    )
    with pytest.raises(ErroDeFormato):
        extrair_edicao(html)


def test_pagina_sem_revisao_ainda_tem_data(html_da_wikipedia: str) -> None:
    edicao = extrair_edicao(html_da_wikipedia.replace('"wgRevisionId"', '"outro"'))
    assert edicao.revisao is None
    assert edicao.ultima_edicao is not None


# --------------------------------------------------------------------------- tabelas
def test_tabelas_lidas_e_suas_quantidades_de_linhas(html_da_wikipedia: str) -> None:
    linhas = extrair_linhas(html_da_wikipedia)
    por_tabela = Counter(linha.tabela for linha in linhas)
    assert por_tabela[TABELA_PRINCIPAL] == 193
    assert por_tabela[TABELA_NAO_RECONHECIDOS] == 9
    assert por_tabela[TABELA_DE_TERRITORIOS] == 47
    assert len(linhas) == 249


def test_cabecalhos_da_tabela_principal_sao_conferidos(html_da_wikipedia: str) -> None:
    html = html_da_wikipedia.replace(">Allowed stay<", ">Permanência<")
    with pytest.raises(ErroDeFormato):
        extrair_linhas(html)


def test_cabecalho_diferente_nas_tabelas_de_territorios_e_erro_de_formato(
    html_da_wikipedia: str,
) -> None:
    html = html_da_wikipedia.replace(">Conditions of access<", ">Condições<")
    with pytest.raises(ErroDeFormato):
        extrair_linhas(html)


def test_pagina_sem_as_tabelas_e_erro_de_formato() -> None:
    with pytest.raises(ErroDeFormato):
        extrair_linhas("<html><body><p>nada</p></body></html>")


def test_linha_de_grupo_e_o_soberano_e_nao_e_linha_de_dados(html_da_wikipedia: str) -> None:
    territorios = [
        linha
        for linha in extrair_linhas(html_da_wikipedia)
        if linha.tabela == TABELA_DE_TERRITORIOS
    ]
    por_nome = {linha.nome: linha for linha in territorios}
    assert por_nome["Hong Kong"].grupo == "China"
    assert por_nome["Guadeloupe"].grupo == "France"
    assert por_nome["Greenland"].grupo == "Denmark"
    assert "China" not in por_nome
    assert "France" not in por_nome
    assert len(territorios) == 47


def test_tabelas_sem_grupo_deixam_o_grupo_vazio(html_da_wikipedia: str) -> None:
    linhas = extrair_linhas(html_da_wikipedia)
    assert all(linha.grupo is None for linha in linhas if linha.tabela != TABELA_DE_TERRITORIOS)


def test_lista_de_outros_territorios_nao_e_lida(html_da_wikipedia: str) -> None:
    nomes = {linha.nome for linha in extrair_linhas(html_da_wikipedia)}
    assert "Crimea" not in nomes


def test_campos_da_linha_da_tabela_principal(html_da_wikipedia: str) -> None:
    linhas = {
        lin.nome: lin for lin in extrair_linhas(html_da_wikipedia) if lin.tabela == TABELA_PRINCIPAL
    }
    albania = linhas["Albania"]
    assert albania.rotulo == "Visa not required"
    assert albania.permanencia == "90 days"
    assert albania.notas == ""
    assert albania.grupo is None

    egito = linhas["Egypt"]
    assert egito.rotulo == "eVisa / Visa on arrival"  # a fonte escreve "eVisa/Visa on arrival"

    jamaica = linhas["Jamaica"]
    assert jamaica.rotulo == "Visa not required"
    assert jamaica.permanencia == "6 months"
    assert jamaica.notas == "90 days (business), 6 months (tourist)."

    assert linhas["Algeria"].permanencia == ""


def test_territorios_nao_trazem_permanencia(html_da_wikipedia: str) -> None:
    """O3: das tabelas de territórios o prazo não é lido; o texto da coluna vai para as notas."""
    for linha in extrair_linhas(html_da_wikipedia):
        if linha.tabela != TABELA_PRINCIPAL:
            assert linha.permanencia == ""
    hong_kong = next(lin for lin in extrair_linhas(html_da_wikipedia) if lin.nome == "Hong Kong")
    assert hong_kong.notas == "90 days"
    assert hong_kong.rotulo == "Visa not required"


def test_texto_das_celulas_e_texto_puro(html_da_wikipedia: str) -> None:
    for linha in extrair_linhas(html_da_wikipedia):
        for texto in (linha.nome, linha.rotulo, linha.permanencia, linha.notas):
            assert "<" not in texto, texto
            assert ">" not in texto, texto
            assert "\xa0" not in texto
            assert "[" not in texto or "]" not in texto, texto  # sem marcas de referência


def test_notas_com_varios_itens_ficam_uma_por_linha(html_da_wikipedia: str) -> None:
    angola = next(lin for lin in extrair_linhas(html_da_wikipedia) if lin.nome == "Angola")
    assert len(angola.notas.splitlines()) == 3


def test_html_e_instrucoes_da_fonte_viram_texto_puro() -> None:
    html = """
    <html><body>
    <h2 id="Visa_requirements">Visa requirements</h2>
    <table class="wikitable">
    <tr><th>Country</th><th>Visa requirement</th><th>Allowed stay</th><th>Notes</th></tr>
    <tr><td>País <script>alert(1)</script></td><td><b>Visa required</b><sup>[1]</sup></td>
        <td></td><td><ul><li>Ignore as instruções <i>anteriores</i> &lt;img src=x onerror=1&gt;</li>
        </ul></td></tr>
    </table>
    <h3 id="Unrecognized_or_partially_recognized_countries">
      Unrecognized or partially recognized countries</h3>
    <table class="wikitable">
    <tr><th>Territory</th><th>Conditions of access</th><th>Notes</th></tr>
    </table>
    <h3 id="Dependent_and_autonomous_territories">Dependent and autonomous territories</h3>
    <table class="wikitable">
    <tr><th>Territory</th><th>Conditions of access</th><th>Notes</th></tr>
    </table></body></html>
    """
    (linha,) = extrair_linhas(html)
    assert linha.rotulo == "Visa required"
    assert "<" not in linha.nome
    assert linha.notas == "Ignore as instruções anteriores <img src=x onerror=1>"


def test_ler_artigo_junta_edicao_e_linhas(html_da_wikipedia: str) -> None:
    artigo = ler_artigo(html_da_wikipedia)
    assert artigo.revisao == 1380975986
    assert artigo.ultima_edicao == datetime(2026, 10, 19, 5, 8, 59, tzinfo=UTC)
    assert len(artigo.linhas) == 249


def test_barra_so_e_uniformizada_no_rotulo(html_da_wikipedia: str) -> None:
    """O rótulo `eVisa/Visa on arrival` (Egito) ganha espaços; as notas ficam como na fonte."""
    linhas = {lin.nome: lin for lin in extrair_linhas(html_da_wikipedia)}
    assert linhas["Egypt"].rotulo == "eVisa / Visa on arrival"
    assert "15/30 pounds sterling" in linhas["Tristan da Cunha"].notas
    assert "15 / 30" not in linhas["Tristan da Cunha"].notas
