"""Cada linha de `contracts/textos-do-chat.md`, e os rótulos iguais aos do painel."""

from datetime import UTC, datetime

import pytest

from farol.chat import textos


# --------------------------------------------------------------------------- datas
def test_data_em_dd_mm_aaaa() -> None:
    assert textos.data(datetime(2026, 10, 23, 12, 0, tzinfo=UTC)) == "23/10/2026"


def test_data_no_fuso_de_sao_paulo() -> None:
    """01h UTC ainda é o dia anterior em Brasília."""
    assert textos.data(datetime(2026, 10, 23, 1, 0, tzinfo=UTC)) == "22/10/2026"


# --------------------------------------------------------------------------- rótulos do painel
def test_rotulos_de_nivel_iguais_aos_de_niveis_ts() -> None:
    assert textos.ROTULOS_DE_NIVEL == {
        "evitar": "Evite viagens não essenciais",
        "nao_viajar": "Não viaje",
    }
    assert textos.ALERTA_SO_REGIONAL == "Alerta só para parte do país"


def test_rotulos_de_visto_iguais_aos_de_vistos_ts() -> None:
    assert textos.ROTULOS_DE_VISTO == {
        "isento": "Isento de visto",
        "visto_na_chegada": "Visto na chegada",
        "autorizacao_eletronica": "Autorização ou visto eletrônico",
        "visto_exigido": "Visto exigido",
        "outra_situacao": "Outra situação",
        "sem_informacao": "Sem informação de visto",
    }
    assert textos.VARIA_CONFORME_O_MOTIVO == "Varia conforme o motivo da viagem"
    assert textos.PERMANENCIA_VARIA == "Varia conforme o motivo (ver observações)"
    assert textos.PERMANENCIA_DIVERGENTE == "Prazos divergentes na fonte (ver observações)"
    assert textos.AVISO_NAO_OFICIAL == (
        "Informação não oficial. Confirme com o consulado ou embaixada do país antes da viagem."
    )
    assert textos.AVISO_VISTO_DESATUALIZADO == (
        "Estes dados podem estar desatualizados: foram lidos da fonte há mais de 14 dias."
    )


def test_portal_consular_igual_ao_do_frontend() -> None:
    assert textos.URL_DO_PORTAL_CONSULAR == "https://www.gov.br/mre/pt-br/assuntos/portal-consular"


# --------------------------------------------------------------------------- frases do alerta
@pytest.mark.parametrize(
    ("nivel", "so_regional", "dados_obtidos", "esperado"),
    [
        ("nao_viajar", False, True,
         'Para Síria, o Itamaraty recomenda não viajar (nível "Não viaje").'),
        ("evitar", False, True,
         "Para Síria, o Itamaraty recomenda evitar viagens não essenciais "
         '(nível "Evite viagens não essenciais").'),
        ("sem_alerta", False, True,
         "Não há alerta de viagem do Itamaraty para Síria. "
         "Isso não significa que o governo recomenda a viagem."),
        ("sem_alerta", True, True,
         'Para Síria, há "Alerta só para parte do país": ele vale só para a região indicada, '
         "não para o país inteiro. Para o restante do país, a ausência de alerta não significa "
         "que o governo recomenda a viagem."),
        ("nao_verificado", False, True,
         "O nível de alerta de Síria não foi verificado: ainda não temos informação confirmada "
         "do Itamaraty."),
        ("nao_verificado", False, False,
         "Ainda não obtivemos os dados do Itamaraty, então o nível de alerta de Síria não foi "
         "verificado."),
    ],
)  # fmt: skip
def test_frase_do_alerta(nivel: str, so_regional: bool, dados_obtidos: bool, esperado: str) -> None:
    assert textos.frase_do_alerta(nivel, "Síria", so_regional, dados_obtidos) == esperado


def test_aviso_de_alerta_desatualizado() -> None:
    assert textos.AVISO_ALERTA_DESATUALIZADO == (
        "Dados desatualizados: a última atualização completa tem mais de 3 dias."
    )


# --------------------------------------------------------------------------- frases do visto
@pytest.mark.parametrize(
    ("situacao", "aceita_rg", "esperado"),
    [
        ("isento", False, "Não, brasileiros não precisam de visto para Chile."),
        ("isento", True,
         "Não, brasileiros não precisam de visto para Chile, e a entrada pode ser feita com o RG."),
        ("visto_na_chegada", False,
         "Brasileiros precisam de visto para Chile, mas ele é obtido na chegada."),
        ("autorizacao_eletronica", False,
         "Brasileiros precisam de uma autorização ou visto eletrônico para Chile, "
         "obtido antes da viagem."),
        ("visto_exigido", False, "Sim, brasileiros precisam de visto para Chile."),
        ("outra_situacao", False,
         "A situação de visto de Chile não se encaixa nas categorias do site."),
        ("sem_informacao", False,
         "Sem informação de visto para Chile. Isso não significa que a entrada seja livre."),
    ],
)  # fmt: skip
def test_frase_do_visto(situacao: str, aceita_rg: bool, esperado: str) -> None:
    assert textos.frase_do_visto(situacao, "Chile", aceita_rg) == esperado


# --------------------------------------------------------------------------- mensagens fixas
def test_qual_dos_paises() -> None:
    assert textos.qual_dos_paises(["A", "B"]) == (
        "Qual deles você quer saber: A ou B? Pergunte de novo com o nome do país."
    )
    assert textos.qual_dos_paises(["A", "B", "C"]) == (
        "Qual deles você quer saber: A, B ou C? Pergunte de novo com o nome do país."
    )


def test_um_pais_por_vez() -> None:
    assert textos.um_pais_por_vez(["A", "B"]) == (
        "Entendi que você perguntou sobre A e B. Pergunte sobre um país de cada vez, por favor."
    )
    assert textos.um_pais_por_vez(["A", "B", "C"]).startswith(
        "Entendi que você perguntou sobre A, B e C."
    )


def test_mensagens_sem_dados() -> None:
    assert textos.PEDIR_PAIS == (
        'De qual país você quer saber? Pergunte citando o nome, por exemplo: "Preciso de visto '
        'para o Japão?"'
    )
    assert textos.BRASIL == (
        "Eu respondo sobre viagens de brasileiros ao exterior. Para qual país você vai?"
    )
    assert textos.FORA_DO_ASSUNTO == (
        "Eu informo o nível de alerta do Itamaraty e a situação de visto para brasileiros em "
        'cada país, por exemplo: "Como está o alerta para o Peru?". Para o resto, como postos e '
        "o conteúdo dos alertas, abra o painel do país no mapa."
    )
    assert textos.REFORMULAR == (
        "Não consegui entender de qual país você fala. Pode reformular citando o nome do país?"
    )


def test_limite_de_perguntas() -> None:
    assert textos.limite_de_perguntas(20, 3) == (
        "Você chegou ao limite de 20 perguntas por hora. Tente de novo em 3 min."
    )
