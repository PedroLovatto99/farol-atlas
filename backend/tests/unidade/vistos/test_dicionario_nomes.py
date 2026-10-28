"""`nomes.yaml`: todo nome da fonte liga a um código do mapa ou é ignorado de propósito."""

import pytest

from farol.vistos.dicionario import Dicionario, carregar_dicionario
from farol.vistos.fonte import LinhaDaFonte
from farol.vistos.normalizacao import chave_de_consulta

# Os 18 nomes que o pycountry não liga sozinho (research.md 3.4)
APELIDOS = {
    "Brunei": "BN",
    "Cape Verde": "CV",
    "Democratic Republic of the Congo": "CD",
    "Micronesia": "FM",
    "Russia": "RU",
    "Turkey": "TR",
    "Vatican City": "VA",
    "United Kingdom and Crown dependencies": "GB",
    "Palestine": "PS",
    "Macau": "MO",
    "Saint Martin": "MF",
    "Sint Maarten": "SX",
    "Pitcairn Islands": "PN",
    "Saint Helena": "SH",
    "Ascension Island": "SH",
    "Tristan da Cunha": "SH",
    "Clipperton Island": "CLP",
    "U.S. Virgin Islands": "VI",
}

# Os 21 nomes ignorados de propósito (research.md 3.4)
IGNORADOS = {
    # por convenção da 001
    "Kosovo",
    "Falkland Islands",
    # território não reconhecido, sem desenho no mapa
    "Abkhazia",
    "South Ossetia",
    "Northern Cyprus",
    "Somaliland",
    "Transnistria",
    # área neutra
    "Sahrawi Arab Democratic Republic",
    # parte de outro país no mapa
    "Guadeloupe",
    "Martinique",
    "Mayotte",
    "Réunion",
    "Bonaire",
    "Sint Eustatius",
    "Saba",
    # sem desenho próprio
    "Tokelau",
    "Jan Mayen",
    "Svalbard",
    "Akrotiri and Dhekelia",
    "British Indian Ocean Territory",
    "South Georgia and the South Sandwich Islands",
}


def test_os_numeros_aprovados() -> None:
    assert len(APELIDOS) == 18
    assert len(IGNORADOS) == 21


def test_todo_nome_da_fixture_esta_em_nomes_ou_em_ignorar(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    """SC-009: nenhuma linha lida do artigo some sem aparecer em um país ou no registro."""
    desconhecidos = [
        linha.nome
        for linha in linhas_da_fonte
        if dicionario_real.ligar_nome(linha.nome).desconhecido
    ]
    assert desconhecidos == []


def test_o_dicionario_tem_so_os_nomes_da_fixture(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    da_fixture = {chave_de_consulta(linha.nome) for linha in linhas_da_fonte}
    assert len(da_fixture) == 249  # sem nome repetido nas três tabelas
    assert set(dicionario_real.nomes) | set(dicionario_real.ignorar) == da_fixture
    assert len(dicionario_real.nomes) == 228
    assert len(dicionario_real.ignorar) == 21


@pytest.mark.parametrize(("nome", "codigo"), sorted(APELIDOS.items()))
def test_apelido_liga_ao_codigo_certo(dicionario_real: Dicionario, nome: str, codigo: str) -> None:
    ligacao = dicionario_real.ligar_nome(nome)
    assert ligacao.codigo == codigo
    assert not ligacao.ignorado


def test_os_ignorados_sao_exatamente_os_21_aprovados_e_cada_um_tem_motivo(
    dicionario_real: Dicionario,
) -> None:
    assert {chave_de_consulta(n) for n in IGNORADOS} == set(dicionario_real.ignorar)
    for nome in IGNORADOS:
        ligacao = dicionario_real.ligar_nome(nome)
        assert ligacao.ignorado, nome
        assert ligacao.codigo is None
        assert ligacao.motivo and len(ligacao.motivo) > 10, nome


def test_nenhum_nome_esta_nas_duas_listas(dicionario_real: Dicionario) -> None:
    assert not set(dicionario_real.nomes) & set(dicionario_real.ignorar)


def test_todo_codigo_existe_no_seed_e_nenhum_e_de_area_neutra(
    dicionario_real: Dicionario, codigos_do_mapa: frozenset[str]
) -> None:
    codigos = set(dicionario_real.nomes.values())
    assert codigos <= codigos_do_mapa
    assert not codigos & {"EH", "AQ"}
    assert "BR" not in codigos  # a fonte não tem linha para o Brasil


def test_a_validacao_contra_o_seed_roda_no_carregamento(
    codigos_do_mapa: frozenset[str],
) -> None:
    """O carregador confere código existente e não neutro (o conteúdo real não pode falhar)."""
    carregar_dicionario(codigos_validos=codigos_do_mapa, codigos_neutros={"EH", "AQ"})


def test_kosovo_e_falkland_islands_sao_ignorados(dicionario_real: Dicionario) -> None:
    assert dicionario_real.ligar_nome("Kosovo").ignorado
    assert dicionario_real.ligar_nome("Falkland Islands").ignorado


def test_reino_unido_e_dependencias_da_coroa_ligam_ao_gb(dicionario_real: Dicionario) -> None:
    assert dicionario_real.ligar_nome("United Kingdom and Crown dependencies").codigo == "GB"


def test_nomes_com_linha_propria_ligam_ao_proprio_codigo(dicionario_real: Dicionario) -> None:
    esperados = {
        "Hong Kong": "HK",
        "Taiwan": "TW",
        "Puerto Rico": "PR",
        "Guam": "GU",
        "Greenland": "GL",
        "Argentina": "AR",
        "Norway": "NO",  # o YAML lê NO sem aspas como falso: o arquivo precisa citar o código
        "São Tomé and Príncipe": "ST",
        "Côte d'Ivoire": "CI",
    }
    for nome, codigo in esperados.items():
        assert dicionario_real.ligar_nome(nome).codigo == codigo, nome


def test_nome_novo_na_fonte_continua_desconhecido(dicionario_real: Dicionario) -> None:
    assert dicionario_real.ligar_nome("Atlantis").desconhecido
