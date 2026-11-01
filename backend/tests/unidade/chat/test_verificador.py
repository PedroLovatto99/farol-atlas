"""Verificador de prosa: descarta o texto do modelo que o código não consegue sustentar.

O que vale é o que os dados dizem: a prosa não chama de seguro, não recomenda, não traz link nem
HTML, não cita país que não está nos dados da resposta e não inventa número.
"""

from datetime import UTC, datetime

import pytest

from farol.chat.ferramentas import TrechoUsado
from farol.chat.protocolos import PaisEncontrado, ResultadoDaResolucao
from farol.chat.verificador import Violacao, verificar_prosa

IRA = PaisEncontrado("IR", "Irã")
ISRAEL = PaisEncontrado("IL", "Israel")
TURQUIA = PaisEncontrado("TR", "Turquia")
CONGO = PaisEncontrado("CG", "Rep. do Congo")
CONGO_RD = PaisEncontrado("CD", "Rep. Dem. do Congo")
NOMES = {"irã": IRA, "israel": ISRAEL, "turquia": TURQUIA}


class ResolvedorFalso:
    def resolver(self, texto: str) -> ResultadoDaResolucao:
        minusculo = texto.lower()
        ambiguos = ((CONGO, CONGO_RD),) if "congo" in minusculo else ()
        return ResultadoDaResolucao(
            encontrados=tuple(p for nome, p in NOMES.items() if nome in minusculo),
            ambiguos=ambiguos,
        )


def trecho(texto: str) -> TrechoUsado:
    return TrechoUsado(
        alerta_id=1,
        titulo="Alerta",
        data=datetime(2026, 10, 1, tzinfo=UTC),
        url="https://gov.br/a",
        vigor="em_vigor",
        inicio=0,
        fim=len(texto),
        trecho=texto,
    )


TRECHOS = [
    trecho(
        "O Ministério recomenda não viajar para o Irã e para Israel. "
        "Em emergência, ligue +98 912 148 5200 e mantenha o passaporte válido por 6 meses."
    )
]
PERGUNTA = "O que o Itamaraty recomenda para o Irã?"


def verificar(texto: str, pergunta: str = PERGUNTA) -> Violacao | None:
    return verificar_prosa(
        texto, trechos=TRECHOS, pergunta=pergunta, paises=(IRA,), resolvedor=ResolvedorFalso()
    )


def test_prosa_fiel_aos_trechos_passa() -> None:
    texto = "O Itamaraty recomenda não viajar para o Irã. Veja o trecho do alerta abaixo."
    assert verificar(texto) is None


def test_pode_citar_pais_que_esta_nos_trechos_usados() -> None:
    assert verificar("O alerta fala do Irã e de Israel.") is None


def test_pode_repetir_numero_que_esta_nos_trechos_ou_na_pergunta() -> None:
    assert verificar("O plantão é +98 912 148 5200; o passaporte deve valer 6 meses.") is None
    assert (
        verificar("Em 2026, o texto diz o mesmo.", pergunta="O que mudou em 2026 no Irã?") is None
    )


@pytest.mark.parametrize(
    "texto",
    [
        "O Irã é seguro para turistas.",
        "Os destinos mais seguros são outros.",
        "Fique tranquilo, não há problema.",
        "Pode viajar sem riscos.",
        "Você pode viajar com calma.",
        "Eu recomendo o Irã nesta época.",
        "Vale a pena ir ao Irã.",
    ],
)
def test_prosa_que_chama_de_seguro_ou_recomenda_e_descartada(texto: str) -> None:
    violacao = verificar(texto)
    assert violacao is not None and violacao.regra == "seguranca_ou_recomendacao"


def test_seguranca_como_substantivo_nao_e_confundida_com_seguro() -> None:
    assert verificar("Siga as orientações de segurança das autoridades do Irã.") is None


@pytest.mark.parametrize(
    "texto",
    [
        "Veja https://www.gov.br/mre/alerta para saber mais.",
        "Acesse www.gov.br/mre.",
        'Veja <a href="x">aqui</a>.',
        "Veja <b>isto</b>.",
        "Veja [o alerta](https://gov.br/a).",
    ],
)
def test_url_html_e_link_de_markdown_sao_descartados(texto: str) -> None:
    violacao = verificar(texto)
    assert violacao is not None and violacao.regra == "link_ou_html"


def test_pais_que_nao_esta_nos_dados_e_descartado() -> None:
    violacao = verificar("O alerta também recomenda cuidado na Turquia.")
    assert violacao is not None
    assert violacao.regra == "pais_fora_dos_dados" and "Turquia" in violacao.detalhe


def test_pais_ambiguo_na_prosa_e_descartado() -> None:
    violacao = verificar("O alerta fala do Congo.")
    assert violacao is not None and violacao.regra == "pais_fora_dos_dados"


def test_pais_da_pergunta_pode_ser_citado_mesmo_fora_dos_trechos() -> None:
    texto = "Não encontrei nada específico sobre a Turquia nos alertas."
    assert verificar(texto, pergunta="E a Turquia?") is None


def test_numero_que_nao_esta_nos_dados_e_descartado() -> None:
    violacao = verificar("O telefone de plantão é +98 912 000 0000.")
    assert violacao is not None
    assert violacao.regra == "numero_fora_dos_dados" and "000" in violacao.detalhe


@pytest.mark.parametrize(
    "texto",
    [
        "O passaporte deve valer seis meses.",  # "6 meses" no trecho
        "O passaporte deve valer Seis meses, e há um plantão.",  # "um" sozinho é artigo
        "O texto pede vinte e um dias.",  # "21 dias" no trecho
    ],
)
def test_numero_por_extenso_e_o_mesmo_que_em_algarismos(texto: str) -> None:
    assert (
        verificar_prosa(
            texto,
            trechos=[trecho("Passaporte válido por 6 meses; aguarde 21 dias.")],
            pergunta="Irã?",
            paises=(IRA,),
            resolvedor=ResolvedorFalso(),
        )
        is None
    )


def test_algarismo_na_prosa_casa_com_numero_por_extenso_no_trecho() -> None:
    assert (
        verificar_prosa(
            "O passaporte deve valer 6 meses; a espera é de 120 dias.",
            trechos=[trecho("Passaporte válido por seis meses; espera de cento e vinte dias.")],
            pergunta="Irã?",
            paises=(IRA,),
            resolvedor=ResolvedorFalso(),
        )
        is None
    )


def test_numero_por_extenso_que_nao_esta_nos_dados_e_descartado() -> None:
    violacao = verificar("O passaporte deve valer sete meses.")
    assert violacao is not None
    assert violacao.regra == "numero_fora_dos_dados" and "7" in violacao.detalhe


def test_sem_trechos_qualquer_numero_e_estranho() -> None:
    violacao = verificar_prosa(
        "São 3 alertas.", trechos=[], pergunta="Alertas?", paises=(), resolvedor=ResolvedorFalso()
    )
    assert violacao is not None and violacao.regra == "numero_fora_dos_dados"
