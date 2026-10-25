"""Extratores da coleta de postos: tabela de repartições e subpáginas de contato.

Usam páginas reais do gov.br salvas em `tests/fixtures/govbr/` (nada de internet). A coleta de
postos é de melhor esforço: o que não for encontrado volta nulo, sem erro.
"""

from pathlib import Path

import pytest

from farol.coleta.extratores import (
    ContatoExtraido,
    extrair_contato,
    extrair_reparticoes,
    links_de_contato,
    sem_rotulos_de_pagina,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "govbr"
URL_DA_TABELA = (
    "https://www.gov.br/mre/pt-br/assuntos/portal-consular/reparticoes-consulares-do-brasil"
)
BASE_MILAO = "https://www.gov.br/mre/pt-br/consulado-milao"
BASE_PRETORIA = "https://www.gov.br/mre/pt-br/embaixada-pretoria"


def ler(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- tabela de repartições
@pytest.fixture(scope="module")
def tabela() -> dict[str, tuple[tuple[str, str], ...]]:
    """País → (nome do posto, link) de cada posto da linha, como a fixture real traz."""
    linhas = extrair_reparticoes(ler("reparticoes.html"), URL_DA_TABELA)
    return {item.pais: tuple((p.nome, p.url) for p in item.postos) for item in linhas}


def test_a_tabela_tem_198_linhas_de_dados() -> None:
    linhas = extrair_reparticoes(ler("reparticoes.html"), URL_DA_TABELA)
    assert len(linhas) == 198


def test_cada_linha_liga_o_pais_ao_posto_que_o_atende(
    tabela: dict[str, tuple[tuple[str, str], ...]],
) -> None:
    assert tabela["Afeganistão"] == (("Islamabade", "http://islamabade.itamaraty.gov.br/pt-br/"),)
    assert tabela["Albânia"] == (("Tirana", "http://tirana.itamaraty.gov.br/pt-br"),)


def test_pais_atendido_por_mais_de_um_posto_traz_todos_e_o_nome_vem_inteiro(
    tabela: dict[str, tuple[tuple[str, str], ...]],
) -> None:
    # no HTML o texto do link é "Pretóri" + "a" solto; o `title` tem o nome certo
    assert tabela["África do Sul"] == (
        ("Pretória", "http://pretoria.itamaraty.gov.br/pt-br/"),
        ("Cidade do Cabo", "http://capetown.itamaraty.gov.br/"),
    )


def test_marcas_de_rodape_saem_do_nome_do_pais(
    tabela: dict[str, tuple[tuple[str, str], ...]],
) -> None:
    assert "Nauru" in tabela
    assert "Luxemburgo" in tabela
    assert not [pais for pais in tabela if "*" in pais or pais != pais.strip()]


def test_o_prefixo_do_tipo_do_posto_sai_do_nome(
    tabela: dict[str, tuple[tuple[str, str], ...]],
) -> None:
    assert tabela["China"][0][0] != ""
    nomes = [nome for postos in tabela.values() for nome, _ in postos]
    assert "Chengdu" in nomes
    assert not [n for n in nomes if n.lower().startswith(("consulado", "embaixada"))]


def test_o_link_do_pais_e_a_url_da_pagina_do_pais() -> None:
    linhas = {
        item.pais: item for item in extrair_reparticoes(ler("reparticoes.html"), URL_DA_TABELA)
    }
    assert linhas["Afeganistão"].pais_url == (
        "https://www.gov.br/mre/pt-br/assuntos/portal-consular/"
        "reparticoes-consulares-do-brasil/regiao/afeganistao/afeganistao"
    )


def test_ha_postos_na_quase_totalidade_das_linhas() -> None:
    linhas = extrair_reparticoes(ler("reparticoes.html"), URL_DA_TABELA)
    sem_posto = [item.pais for item in linhas if not item.postos]
    assert len(sem_posto) <= 5, sem_posto
    assert all(p.url.startswith("http") for item in linhas for p in item.postos)


def test_pagina_sem_tabela_devolve_vazio_sem_erro() -> None:
    assert extrair_reparticoes("<html><body><p>nada</p></body></html>", URL_DA_TABELA) == ()
    assert extrair_reparticoes("", URL_DA_TABELA) == ()


def test_link_relativo_e_resolvido_a_partir_da_pagina() -> None:
    html = (
        "<table><tr><td>Onde você está:</td><td>Onde obter:</td></tr>"
        '<tr><td><a href="/pais/x">Xlândia</a></td>'
        '<td><a href="/mre/pt-br/embaixada-x">Xis</a></td></tr></table>'
    )
    [linha] = extrair_reparticoes(html, URL_DA_TABELA)
    assert linha.pais == "Xlândia"
    assert linha.pais_url == "https://www.gov.br/pais/x"
    assert [(p.nome, p.url) for p in linha.postos] == [
        ("Xis", "https://www.gov.br/mre/pt-br/embaixada-x")
    ]


# --------------------------------------------------------------------------- telefone de plantão
def test_telefone_de_plantao_do_posto_e_nao_o_do_ministerio() -> None:
    contato = extrair_contato(ler("milao_emergencias.html"))
    assert contato.telefone_plantao == "+39 335 727 8117"
    # a página cita também o plantão do Ministério, em Brasília: outro telefone, não o do posto
    assert "98260" not in (contato.telefone_plantao or "")


def test_telefone_com_rotulo_e_parenteses() -> None:
    html = "<div id='content-core'><p>Telefone do plantão consular: (+27) 82 123 4567</p></div>"
    assert extrair_contato(html).telefone_plantao == "(+27) 82 123 4567"


def test_so_o_plantao_do_ministerio_nao_vale_como_telefone_do_posto() -> None:
    html = (
        "<div id='content-core'><p>Telefone do Plantão Consular do Ministério das Relações "
        "Exteriores: +55 (61) 98260-0610</p></div>"
    )
    assert extrair_contato(html).telefone_plantao is None


def test_numero_curto_demais_nao_e_telefone() -> None:
    html = "<div id='content-core'><p>Plantão consular: 112</p></div>"
    assert extrair_contato(html).telefone_plantao is None


def test_a_frase_sobre_o_plantonista_nao_vira_telefone() -> None:
    html = (
        "<div id='content-core'><p>As dúvidas serão respondidas pelo plantonista de emergência. "
        "Nestes casos, favor usar o Fale Conosco. O prazo é de 24 horas úteis, "
        "ou 2026 12345678.</p></div>"
    )
    assert extrair_contato(html).telefone_plantao is None


# --------------------------------------------------------------------------- endereço
def test_endereco_vem_do_titulo_endereco_e_para_antes_da_localizacao_e_do_telefone() -> None:
    contato = extrair_contato(ler("pretoria_fale_conosco.html"))
    assert contato.endereco is not None
    assert contato.endereco.startswith("152 Dallas Avenue, Corobay Corner Building")
    assert contato.endereco.endswith("Pretoria, 0181, Gauteng, África do Sul")
    assert "Google Maps" not in contato.endereco
    assert "Telefone" not in contato.endereco


def test_a_pagina_de_pretoria_nao_tem_telefone_de_plantao() -> None:
    assert extrair_contato(ler("pretoria_fale_conosco.html")).telefone_plantao is None


def test_endereco_dentro_de_address() -> None:
    html = "<body><address>Rua das Flores, 10<br>Lisboa, Portugal</address></body>"
    assert extrair_contato(html).endereco == "Rua das Flores, 10, Lisboa, Portugal"


def test_endereco_na_mesma_linha_do_rotulo() -> None:
    html = "<div id='content-core'><p>Endereço: Avenida Central, 100 - Lima</p></div>"
    assert extrair_contato(html).endereco == "Avenida Central, 100 - Lima"


@pytest.mark.parametrize(
    "arquivo",
    ["milao_fale_conosco.html", "milao_horarios_como_chegar.html"],
)
def test_endereco_de_email_nao_e_endereco(arquivo: str) -> None:
    # "Endereços de e-mail e telefones para entrar em contato" não é um endereço de rua
    assert extrair_contato(ler(arquivo)).endereco is None


# --------------------------------------------------------------------------- páginas sem os dados
@pytest.mark.parametrize(
    "arquivo",
    ["posto_1.html", "posto_2.html", "milao_horarios_como_chegar.html", "pretoria_inicio.html"],
)
def test_pagina_sem_esses_dados_devolve_nulo_sem_erro(arquivo: str) -> None:
    assert extrair_contato(ler(arquivo)) == ContatoExtraido(endereco=None, telefone_plantao=None)


@pytest.mark.parametrize("html", ["", "   ", "<html></html>", "<p>texto solto</p>", "\x00\x01"])
def test_html_vazio_ou_estranho_nao_quebra(html: str) -> None:
    assert extrair_contato(html) == ContatoExtraido(endereco=None, telefone_plantao=None)


# --------------------------------------------------------------------------- links de contato
def test_links_de_contato_de_milao_emergencias_primeiro() -> None:
    assert links_de_contato(ler("posto_2.html"), BASE_MILAO) == [
        f"{BASE_MILAO}/emergencias",
        f"{BASE_MILAO}/fale-conosco-1",
    ]


def test_links_de_contato_de_pretoria() -> None:
    assert links_de_contato(ler("pretoria_inicio.html"), BASE_PRETORIA) == [
        f"{BASE_PRETORIA}/fale-conosco-1",
        f"{BASE_PRETORIA}/assistencia-a-brasileiros",
    ]


def test_links_genericos_do_site_e_de_outros_postos_ficam_de_fora() -> None:
    # "Emergências no Exterior" e "Fale conosco" do menu geral do MRE não são do posto
    links = links_de_contato(ler("posto_2.html"), BASE_MILAO)
    assert all(item.startswith(f"{BASE_MILAO}/") for item in links)
    assert links_de_contato(ler("posto_1.html"), "https://www.gov.br/mre/pt-br/embaixada-ama") == []


def test_limite_de_links_e_respeitado() -> None:
    assert len(links_de_contato(ler("posto_2.html"), BASE_MILAO, limite=1)) == 1


def test_pagina_sem_links_de_contato() -> None:
    assert links_de_contato("", BASE_MILAO) == []
    assert links_de_contato("<html><body><a>sem href</a></body></html>", BASE_MILAO) == []


# --------------------------------------------------------------------------- endereços de lixo
# Casos vistos na coleta real: títulos, rótulos e redes sociais não são endereço.
def endereco_de(corpo: str) -> str | None:
    return extrair_contato(f"<div id='content-core'>{corpo}</div>").endereco


@pytest.mark.parametrize(
    "corpo",
    [
        "<h3>Endereço e contatos</h3><p>Telefone: +1 202 555 0100</p>",
        "<h3>Endereço do Consulado-Geral</h3>",
        "<h3>ENDEREÇO DO CONSULADO-GERAL DO BRASIL EM CHENGDU</h3>",
        "<h3>Endereço/Address:</h3>",
        "<p>Endereço:</p><p>Fale conosco</p>",
        "<p>Endereço: Brasília</p>",  # curto e sem número: não é endereço de rua
    ],
    ids=["e-contatos", "do-consulado", "maiusculas", "bilingue", "so-rotulo", "sem-numero"],
)
def test_titulos_e_rotulos_nao_viram_endereco(corpo: str) -> None:
    assert endereco_de(corpo) is None


def test_titulo_com_o_endereco_nas_linhas_seguintes_continua_valendo() -> None:
    corpo = "<h3>Endereço do Consulado-Geral</h3><p>Rua Bela, 25<br/>Lisboa 1000-001</p>"
    assert endereco_de(corpo) == "Rua Bela, 25, Lisboa 1000-001"


def test_linha_so_com_pontuacao_e_ignorada() -> None:
    corpo = "<p>Endereço</p><p>:</p><p>Calle de Goya, 5-7<br/>28001 Madrid</p>"
    assert endereco_de(corpo) == "Calle de Goya, 5-7, 28001 Madrid"


def test_linhas_vazias_no_meio_do_endereco_nao_deixam_virgulas_soltas() -> None:
    corpo = "<p>Endereço</p><p>Kungsgatan 88<br/> <br/>112 27, Stockholm</p>"
    assert endereco_de(corpo) == "Kungsgatan 88, 112 27, Stockholm"


def test_o_endereco_para_no_proximo_rotulo_e_nas_redes_sociais() -> None:
    corpo = (
        "<p>Endereço</p><p>KN 5 Rd, Kigali, Ground Floor<br/>Instagram:<br/>@brazilinrwanda<br/>"
        "Emergências:<br/>O plantão atende 24 horas</p>"
    )
    assert endereco_de(corpo) == "KN 5 Rd, Kigali, Ground Floor"


def test_o_endereco_para_antes_de_estacao_proxima_e_outros_rotulos_com_dois_pontos() -> None:
    corpo = (
        "<p>Endereço</p><p>56 Avenue Robert Schuman, 3º andar, 13002, Marselha.<br/>"
        "Estação mais próxima:<br/>Metrô Joliette</p>"
    )
    assert endereco_de(corpo) == "56 Avenue Robert Schuman, 3º andar, 13002, Marselha."


def test_nome_da_representacao_no_inicio_nao_faz_parte_do_endereco() -> None:
    corpo = (
        "<p>Endereço</p><p>Embaixada do Brasil na Índia e no Butão<br/>"
        "8, Dr. APJ Abdul Kalam Road, New Delhi - 110011</p>"
    )
    assert endereco_de(corpo) == "8, Dr. APJ Abdul Kalam Road, New Delhi - 110011"


def test_endereco_com_email_ou_link_nao_vale() -> None:
    assert endereco_de("<p>Endereço: escreva para contato@exemplo.gov.br, 10</p>") is None
    assert endereco_de("<p>Endereço</p><p>https://exemplo.gov.br/mapa 10</p>") is None


def test_endereco_sem_numero_mas_com_s_n_vale() -> None:
    assert endereco_de("<p>Endereço: Avenida das Nações, s/n, Brasília</p>") is not None


# --------------------------------------------------------------------------- segunda rodada real
# Casos de postos reais (Amsterdã, Cidade do Cabo, Díli, Vancouver, Copenhague, Hamamatsu...)
def test_tag_dentro_da_linha_nao_parte_o_endereco() -> None:
    corpo = (
        "<p>Endereço</p><p>Strawinskylaan 481, Torre 3 - 4<sup>º</sup> andar<br/>"
        "1077XX Amsterdam</p>"
    )
    assert endereco_de(corpo) == "Strawinskylaan 481, Torre 3 - 4º andar, 1077XX Amsterdam"


def test_menu_do_site_depois_do_endereco_fica_de_fora() -> None:
    corpo = (
        "<p>Endereço</p><p>7 Bree Street, Touchstone House<br/>8001 Cape Town</p>"
        "<ul><li>Composição</li><li>Organograma</li><li>Quem é Quem</li></ul>"
    )
    assert endereco_de(corpo) == "7 Bree Street, Touchstone House, 8001 Cape Town"


def test_menu_sem_endereco_nao_e_endereco() -> None:
    corpo = (
        "<p>Endereço</p><ul><li>Serviços Consulares</li><li>Processo Seletivo 2026</li>"
        "<li>Bolsa de Estudos</li></ul>"
    )
    assert endereco_de(corpo) is None


def test_frase_depois_do_endereco_fica_de_fora() -> None:
    corpo = (
        "<p>Endereço</p><p>1111 Melville St, Suite 1050, Vancouver, BC V6E 3V6, Canada<br/>"
        "O consulado não possui atendimento telefônico para consultas sobre serviços "
        "consulares.<br/>Por favor NÃO ligue para o plantão</p>"
    )
    assert endereco_de(corpo) == "1111 Melville St, Suite 1050, Vancouver, BC V6E 3V6, Canada"


def test_aviso_antes_do_endereco_e_pulado() -> None:
    corpo = (
        "<p>Endereço</p><p>Presencial (apenas por agendamento)/In-person (by appointment only)"
        "<br/>Jens Kofods Gade 1, st th., 1268 Copenhagen K<br/>Em caso de emergências</p>"
    )
    assert endereco_de(corpo) == "Jens Kofods Gade 1, st th., 1268 Copenhagen K"


def test_endereco_da_sede_em_brasilia_nao_e_do_posto() -> None:
    assert (
        endereco_de("<p>Endereço: Setor Bancário Sul, Quadra 01, Blocos H/I, Lote 26/27</p>")
        is None
    )
    assert (
        endereco_de("<p>Endereço</p><p>Esplanada dos Ministérios, Bloco H<br/>70170-900</p>")
        is None
    )


def test_rotulo_no_meio_da_linha_encerra_o_endereco() -> None:
    corpo = (
        "<p>Endereço</p><p>56 Avenue Robert Schuman, 3<sup>º</sup> andar, 13002, Marselha."
        "<br/>Estação mais próxima: Joliette</p>"
    )
    assert endereco_de(corpo) == "56 Avenue Robert Schuman, 3º andar, 13002, Marselha."


def test_horario_entre_parenteses_nao_entra_no_telefone() -> None:
    html = "<div id='content-core'><p>Plantão consular: +964 780 929 1396 (24 horas)</p></div>"
    assert extrair_contato(html).telefone_plantao == "+964 780 929 1396"


def test_endereco_na_mesma_linha_do_titulo_segue_nas_linhas_de_baixo() -> None:
    corpo = (
        "<p>Endereço: 7 Bree Street, Touchstone House</p><p>9th floor - unit 901</p>"
        "<p>8001 - Cape Town</p><ul><li>Composição</li><li>Organograma</li></ul>"
    )
    assert (
        endereco_de(corpo)
        == "7 Bree Street, Touchstone House, 9th floor - unit 901, 8001 - Cape Town"
    )


def test_linhas_curtas_antes_do_numero_fazem_parte_do_endereco() -> None:
    corpo = (
        "<p>Endereço</p><p>Al-Harthia, Zaitoun Street</p><p>Quarter 213, Bagdá</p>"
        "<p>Contatos</p><p>Telefone: +964 780 196 6998</p>"
    )
    assert endereco_de(corpo) == "Al-Harthia, Zaitoun Street, Quarter 213, Bagdá"


def test_instrucoes_de_como_chegar_nao_sao_endereco() -> None:
    corpo = (
        "<p>Endereço</p><p>Seguir pela rodovia I-95, sentido Sul, até o seu término quando "
        "esta fará "
        "junção com a via US-1. Siga pela US-1, sentido sul, até a SW 40th St e vire à direita.</p>"
    )
    assert endereco_de(corpo) is None


# ------------------------------------------------------------ rótulos da página colados no endereço
# Terceira rodada real: 8 dos 76 endereços vieram com o rótulo de um título da página colado no
# começo ou no fim. Só se cortam os rótulos vistos; outros ficam para o usuário decidir.
OS_8_DA_COLETA_REAL = [
    # (posto, como veio, como deve ficar)
    (
        95,
        "Consulate-General of Brazil in Houston, 5444 Westheimer Rd - Suite 1900, "
        "Houston, TX, USA 77056",
        "5444 Westheimer Rd - Suite 1900, Houston, TX, USA 77056",
    ),
    (
        96,
        "Consulate General of Brazil, 6222 Wilshire Boulevard Suite 600, "
        "Los Angeles, California 90048-5100",
        "6222 Wilshire Boulevard Suite 600, Los Angeles, California 90048-5100",
    ),
    (
        100,
        "300 Montgomery St, Suite 300, San Francisco, CA 94104, Jurisdição",
        "300 Montgomery St, Suite 300, San Francisco, CA 94104",
    ),
    (
        111,
        "Embassy of Brazil, United Tower, Building 316, Road 4609, Block 346, 26th floor, Manama, "
        "Kingdom of Bahrain, Kingdom of Bahrain - BAH, Emergências Consulares",
        "United Tower, Building 316, Road 4609, Block 346, 26th floor, Manama, Kingdom of Bahrain, "
        "Kingdom of Bahrain - BAH",
    ),
    (
        136,
        "Address, Chundevi Marg, H-155, Maharajgunj, Kathmandu 44600, Nepal, Endereço Postal, "
        "Postal Address",
        "Chundevi Marg, H-155, Maharajgunj, Kathmandu 44600, Nepal",
    ),
    (
        170,
        "444, Chemin Saint Antoine, BP 793, 97300 Cayenne CEDEX, Guyane française, Jurisdição",
        "444, Chemin Saint Antoine, BP 793, 97300 Cayenne CEDEX, Guyane française",
    ),
    (
        195,
        "Embassy of Brazil, Trg republike 3, 7th floor, 1000 Ljubljana, Slovenia",
        "Trg republike 3, 7th floor, 1000 Ljubljana, Slovenia",
    ),
    (
        209,
        "Endereço da chancelaria, LEVEL 15, Maritime Tower, 10 Customhouse Quay, Wellington, 6011, "
        "Endereço Postal",
        "LEVEL 15, Maritime Tower, 10 Customhouse Quay, Wellington, 6011",
    ),
]


@pytest.mark.parametrize(
    ("veio", "esperado"),
    [(veio, esperado) for _, veio, esperado in OS_8_DA_COLETA_REAL],
    ids=[str(posto) for posto, _, _ in OS_8_DA_COLETA_REAL],
)
def test_corta_os_rotulos_vistos_no_comeco_e_no_fim_do_endereco(veio: str, esperado: str) -> None:
    assert sem_rotulos_de_pagina(veio) == esperado


@pytest.mark.parametrize(
    "endereco",
    [
        "Rua A, 10, Kingdom of Bahrain - BAH",  # parece rótulo, mas é parte do endereço
        "Rua A, 10, Jurisdição, São Paulo, 01000",  # rótulo no meio não se corta
        "Rua A, 10, Mailing Address",  # rótulo parecido que nunca vimos: não se corta
        "Address Road, 5, Londres",  # só vale o rótulo inteiro, seguido de vírgula
        "Embassy Row, 3100, Washington",
        "Rua do Consulado, 10, Lisboa 1000-001",
    ],
)
def test_nao_corta_o_que_nao_e_um_dos_rotulos_vistos(endereco: str) -> None:
    assert sem_rotulos_de_pagina(endereco) == endereco


def test_corta_rotulos_repetidos_e_em_qualquer_caixa() -> None:
    assert (
        sem_rotulos_de_pagina("ADDRESS, Rua A, 10, endereço postal, Postal Address") == "Rua A, 10"
    )


def pagina_com(*linhas: str) -> str:
    return "".join(f"<p>{linha}</p>" for linha in linhas)


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        (
            pagina_com(
                "Endereço",
                "300 Montgomery St<br/>Suite 300<br/>San Francisco, CA 94104",
                "Jurisdição",
            ),
            "300 Montgomery St, Suite 300, San Francisco, CA 94104",
        ),
        (
            pagina_com(
                "Endereço",
                "Address",
                "Chundevi Marg, H-155, Maharajgunj",
                "Kathmandu 44600, Nepal",
                "Endereço Postal",
                "Postal Address",
            ),
            "Chundevi Marg, H-155, Maharajgunj, Kathmandu 44600, Nepal",
        ),
        (
            pagina_com(
                "Endereço da chancelaria",
                "Endereço da chancelaria",
                "LEVEL 15, Maritime Tower",
                "10 Customhouse Quay, Wellington, 6011",
                "Endereço Postal",
            ),
            "LEVEL 15, Maritime Tower, 10 Customhouse Quay, Wellington, 6011",
        ),
        (
            pagina_com(
                "Endereço",
                "Embassy of Brazil",
                "Trg republike 3",
                "7th floor",
                "1000 Ljubljana, Slovenia",
            ),
            "Trg republike 3, 7th floor, 1000 Ljubljana, Slovenia",
        ),
        (
            pagina_com(
                "Endereço",
                "Consulate-General of Brazil in Houston",
                "5444 Westheimer Rd - Suite 1900",
                "Houston, TX, USA 77056",
            ),
            "5444 Westheimer Rd - Suite 1900, Houston, TX, USA 77056",
        ),
    ],
    ids=["jurisdicao-no-fim", "address-e-postal", "chancelaria-e-postal", "embassy", "consulate"],
)
def test_pagina_com_rotulos_de_titulo_em_volta_do_endereco(corpo: str, esperado: str) -> None:
    assert endereco_de(corpo) == esperado
