"""Ligação dos links da tabela de repartições aos postos do banco (por cidade, tipo e país)."""

from decimal import Decimal

from farol.coleta import associar_postos
from farol.coleta.extratores import LinhaDeReparticao, LinkDePosto
from farol.dominio import Posto, TipoPosto

PAISES = {
    "italia": "IT",
    "vaticano": "VA",
    "malta": "MT",
    "afeganistao": "AF",
    "paquistao": "PK",
    "guatemala": "GT",
    "nauru": "NR",
    "australia": "AU",
    "singapura": "SG",
}


def posto(posto_id: int, codigo: str, cidade: str, tipo: TipoPosto) -> Posto:
    return Posto(
        id=posto_id,
        territorio_codigo=codigo,
        cidade=cidade,
        tipo=tipo,
        latitude=Decimal("1.00000"),
        longitude=Decimal("1.00000"),
    )


def linha(pais: str, *links: tuple[str, str]) -> LinhaDeReparticao:
    return LinhaDeReparticao(
        pais=pais, pais_url=None, postos=tuple(LinkDePosto(nome, url) for nome, url in links)
    )


def test_cidade_com_um_so_posto_liga_sem_duvida_ignorando_acentos_e_caixa() -> None:
    postos = [posto(1, "PK", "Islamabade", TipoPosto.EMBAIXADA)]
    ligados = associar_postos(
        [linha("Afeganistão", ("ISLAMABADE", "http://islamabade.itamaraty.gov.br/pt-br/"))],
        postos,
        PAISES,
    )
    assert ligados == {"http://islamabade.itamaraty.gov.br/pt-br/": 1}


def test_um_pais_sem_posto_proprio_liga_ao_posto_de_outro_pais() -> None:
    # Afeganistão é atendido por Islamabade (Paquistão): o país da linha não entra na conta
    postos = [posto(1, "PK", "Islamabade", TipoPosto.EMBAIXADA)]
    ligados = associar_postos([linha("Afeganistão", ("Islamabade", "http://i/"))], postos, PAISES)
    assert ligados == {"http://i/": 1}


def test_apelidos_de_cidade_da_tabela() -> None:
    postos = [
        posto(1, "AU", "Camberra", TipoPosto.EMBAIXADA),
        posto(2, "SG", "Singapura", TipoPosto.EMBAIXADA),
        posto(3, "GT", "Cidade da Guatemala", TipoPosto.EMBAIXADA),
    ]
    ligados = associar_postos(
        [
            linha("Nauru**", ("Cambera", "http://c/")),
            linha("Singapura", ("Cingapura", "http://s/")),
            linha("Guatemala", ("Guatemala", "http://g/")),
        ],
        postos,
        PAISES,
    )
    assert ligados == {"http://c/": 1, "http://s/": 2, "http://g/": 3}


def test_cidade_com_embaixada_e_consulado_o_link_de_consulado_vai_para_o_consulado() -> None:
    postos = [
        posto(1, "FR", "Paris", TipoPosto.EMBAIXADA),
        posto(2, "FR", "Paris", TipoPosto.CONSULADO_GERAL),
    ]
    assert associar_postos(
        [linha("França", ("Paris", "http://cgparis.itamaraty.gov.br/pt-br/"))], postos, PAISES
    ) == {"http://cgparis.itamaraty.gov.br/pt-br/": 2}


def test_link_que_diz_embaixada_vai_para_a_embaixada() -> None:
    postos = [
        posto(1, "FR", "Paris", TipoPosto.EMBAIXADA),
        posto(2, "FR", "Paris", TipoPosto.CONSULADO_GERAL),
    ]
    ligados = associar_postos(
        [linha("França", ("Paris", "https://www.gov.br/mre/pt-br/embaixada-paris"))],
        postos,
        PAISES,
    )
    assert ligados == {"https://www.gov.br/mre/pt-br/embaixada-paris": 1}


def test_sem_pista_de_tipo_e_com_varios_postos_na_cidade_nao_adivinha() -> None:
    postos = [
        posto(1, "FR", "Paris", TipoPosto.EMBAIXADA),
        posto(2, "FR", "Paris", TipoPosto.CONSULADO_GERAL),
    ]
    assert (
        associar_postos([linha("França", ("Paris", "http://paris.exemplo/"))], postos, PAISES) == {}
    )


def test_roma_tem_duas_embaixadas_e_um_consulado_o_pais_da_linha_desempata() -> None:
    postos = [
        posto(1, "IT", "Roma", TipoPosto.EMBAIXADA),
        posto(2, "VA", "Roma", TipoPosto.EMBAIXADA),
        posto(3, "IT", "Roma", TipoPosto.CONSULADO_GERAL),
    ]
    ligados = associar_postos(
        [
            linha("Itália", ("Roma", "http://www.consuladobrasilroma.it/")),
            linha("Malta", ("Roma", "http://cgroma.itamaraty.gov.br/pt-br/")),
            linha("Vaticano", ("Roma", "https://www.gov.br/mre/pt-br/embaixada-vaticano")),
        ],
        postos,
        PAISES,
    )
    assert ligados["http://www.consuladobrasilroma.it/"] == 3
    assert ligados["http://cgroma.itamaraty.gov.br/pt-br/"] == 3
    assert ligados["https://www.gov.br/mre/pt-br/embaixada-vaticano"] == 2


def test_link_para_cidade_sem_posto_no_banco_e_ignorado() -> None:
    postos = [posto(1, "PK", "Islamabade", TipoPosto.EMBAIXADA)]
    ligados = associar_postos(
        [linha("Brasil", ("Belo Horizonte", "http://ereminas.itamaraty.gov.br/pt-br/"))],
        postos,
        PAISES,
    )
    assert ligados == {}


def test_o_mesmo_link_em_varias_linhas_liga_uma_vez() -> None:
    postos = [posto(1, "BE", "Bruxelas", TipoPosto.CONSULADO_GERAL)]
    ligados = associar_postos(
        [
            linha("Bélgica", ("Bruxelas", "http://cgbruxelas.itamaraty.gov.br/pt-br/")),
            linha("Luxemburgo", ("Bruxelas", "http://cgbruxelas.itamaraty.gov.br/pt-br/")),
        ],
        postos,
        PAISES,
    )
    assert ligados == {"http://cgbruxelas.itamaraty.gov.br/pt-br/": 1}
