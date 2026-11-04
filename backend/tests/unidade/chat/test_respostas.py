"""Parágrafos de alerta e de visto a partir das visões (visões falsas, sem banco)."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from farol.chat import Paragrafo, Trecho
from farol.chat.respostas import paragrafos_do_alerta, paragrafos_do_visto
from farol.chat.textos import URL_DO_PORTAL_CONSULAR

DATA = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
MODIFICADO = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
PROIBIDAS = ("seguro", "segura", "tranquilo", "tranquila", "sem perigo", "pode ir")
URL_DO_ALERTA = "https://www.gov.br/mre/alerta-1"
URL_DA_WIKIPEDIA = "https://en.wikipedia.org/wiki/Visa"


@dataclass(frozen=True)
class Regiao:
    nome: str
    nivel: str


@dataclass(frozen=True)
class Alerta:
    titulo: str = "Alerta consular"
    url: str = URL_DO_ALERTA
    publicado_em: datetime = DATA
    modificado_em: datetime | None = None
    define_nivel: bool = True
    pendente: bool = False


@dataclass(frozen=True)
class Painel:
    codigo: str = "SY"
    nome: str = "Síria"
    nivel: str = "sem_alerta"
    regioes: tuple[Regiao, ...] = ()
    regiao_unica_do_alerta: bool = False
    observacao: str | None = None
    alertas: tuple[Alerta, ...] = ()


@dataclass(frozen=True)
class Mapa:
    dados_obtidos: bool = True
    atualizado_em: datetime | None = DATA
    desatualizado: bool = False
    territorios: tuple[()] = ()


@dataclass(frozen=True)
class Fonte:
    nome: str = "Wikipédia: Visa"
    url: str = URL_DA_WIKIPEDIA
    licenca: str | None = "CC BY-SA"


@dataclass(frozen=True)
class Permanencia:
    tipo: str
    texto: str | None = None


@dataclass(frozen=True)
class Observacao:
    texto_original: str
    traducao: str | None = None


@dataclass(frozen=True)
class Visto:
    situacao: str = "isento"
    rotulo_original: str | None = "Visa not required"
    aceita_rg: bool = False
    varia_conforme_motivo: bool = False
    permanencia: Permanencia | None = None
    observacoes: tuple[Observacao, ...] = ()
    origem: str | None = "proprio"
    soberano_nome: str | None = None
    territorio_nome: str | None = None
    dado_de: datetime | None = DATA
    desatualizado: bool = False
    fonte: Fonte = field(default_factory=Fonte)


def textos_de(paragrafos: Sequence[Paragrafo]) -> list[str]:
    return ["".join(t.texto for t in p) for p in paragrafos]


def urls_de(paragrafos: Sequence[Paragrafo]) -> set[str]:
    return {t.url for p in paragrafos for t in p if t.url is not None}


# --------------------------------------------------------------------------- alerta
def test_alerta_na_ordem_frase_dados_observacao_fonte_e_aviso() -> None:
    painel = Painel(
        nivel="evitar",
        regioes=(Regiao("Damasco", "nao_viajar"), Regiao("Alepo", "evitar")),
        observacao="Uma observação.",
        alertas=(Alerta(modificado_em=MODIFICADO),),
    )
    assert textos_de(paragrafos_do_alerta(painel, Mapa(desatualizado=True))) == [
        "Para Síria, o Itamaraty recomenda evitar viagens não essenciais "
        '(nível "Evite viagens não essenciais").',
        'Regiões com nível próprio: Damasco ("Não viaje"); Alepo ("Evite viagens não essenciais").',
        "Alerta que define o nível: Alerta consular "
        "(publicado em 23/10/2026; modificado em 25/10/2026)",
        "Observação: Uma observação.",
        "Fonte: Portal Consular do Itamaraty, atualizado em 23/10/2026.",
        "Dados desatualizados: a última atualização completa tem mais de 3 dias.",
    ]


def test_alerta_sem_data_de_modificacao() -> None:
    painel = Painel(nivel="nao_viajar", alertas=(Alerta(),))
    assert textos_de(paragrafos_do_alerta(painel, Mapa()))[1] == (
        "Alerta que define o nível: Alerta consular (publicado em 23/10/2026)"
    )


def test_so_o_alerta_que_define_o_nivel_aparece() -> None:
    painel = Painel(nivel="evitar", alertas=(Alerta("Antigo", define_nivel=False), Alerta("Atual")))
    texto = " ".join(textos_de(paragrafos_do_alerta(painel, Mapa())))
    assert "Atual" in texto
    assert "Antigo" not in texto


def test_sem_alerta_sem_dados_extras() -> None:
    assert textos_de(paragrafos_do_alerta(Painel(), Mapa())) == [
        "Não há alerta de viagem do Itamaraty para Síria. "
        "Isso não significa que o governo recomenda a viagem.",
        "Fonte: Portal Consular do Itamaraty, atualizado em 23/10/2026.",
    ]


def test_so_regional() -> None:
    painel = Painel(regioes=(Regiao("Norte", "evitar"),), regiao_unica_do_alerta=True)
    resultado = textos_de(paragrafos_do_alerta(painel, Mapa()))
    assert resultado[0].startswith('Para Síria, há "Alerta só para parte do país"')
    assert resultado[1] == 'Regiões com nível próprio: Norte ("Evite viagens não essenciais").'


def test_nao_verificado_com_coleta_e_alerta_pendente() -> None:
    painel = Painel(nivel="nao_verificado", alertas=(Alerta(pendente=True),))
    paragrafos = paragrafos_do_alerta(painel, Mapa())
    assert textos_de(paragrafos)[:2] == [
        "O nível de alerta de Síria não foi verificado: ainda não temos informação confirmada "
        "do Itamaraty.",
        "Confira o alerta original: Alerta consular",
    ]
    assert Trecho("Alerta consular", URL_DO_ALERTA) in paragrafos[1]


def test_nao_verificado_sem_coleta_nao_tem_data_na_fonte() -> None:
    mapa = Mapa(dados_obtidos=False, atualizado_em=None)
    assert textos_de(paragrafos_do_alerta(Painel(nivel="nao_verificado"), mapa)) == [
        "Ainda não obtivemos os dados do Itamaraty, então o nível de alerta de Síria não foi "
        "verificado.",
        "Fonte: Portal Consular do Itamaraty.",
    ]


def test_links_do_alerta_sao_so_o_gov_br_e_o_portal() -> None:
    painel = Painel(nivel="evitar", alertas=(Alerta(),))
    paragrafos = paragrafos_do_alerta(painel, Mapa())
    assert urls_de(paragrafos) == {URL_DO_ALERTA, URL_DO_PORTAL_CONSULAR}


# --------------------------------------------------------------------------- visto
def test_visto_na_ordem_frase_dados_observacao_fonte_e_avisos() -> None:
    visto = Visto(
        situacao="visto_exigido",
        rotulo_original="Visa required",
        varia_conforme_motivo=True,
        permanencia=Permanencia("padronizada", "90 dias"),
        observacoes=(Observacao("Original", "Traduzida"), Observacao("Only English")),
        desatualizado=True,
    )
    assert textos_de(paragrafos_do_visto(visto, "Chile")) == [
        "Sim, brasileiros precisam de visto para Chile.",
        'Categoria: "Visto exigido"',
        "Na fonte: Visa required",
        "Varia conforme o motivo da viagem",
        "Permanência: 90 dias",
        "Observação da fonte (tradução automática): Traduzida",
        "Observação da fonte (não traduzido): Only English",
        "Fonte: Wikipédia: Visa (CC BY-SA, não oficial), dado de 23/10/2026.",
        "Informação não oficial. Confirme com o consulado ou embaixada do país antes da viagem.",
        "Estes dados podem estar desatualizados: foram lidos da fonte há mais de 14 dias.",
    ]


@pytest.mark.parametrize(
    ("situacao", "inicio", "categoria"),
    [
        ("isento", "Não, brasileiros", "Isento de visto"),
        ("visto_na_chegada", "Brasileiros precisam de visto", "Visto na chegada"),
        (
            "autorizacao_eletronica",
            "Brasileiros precisam de uma",
            "Autorização ou visto eletrônico",
        ),
        ("visto_exigido", "Sim, brasileiros", "Visto exigido"),
        ("outra_situacao", "A situação de visto", "Outra situação"),
        ("sem_informacao", "Sem informação", "Sem informação de visto"),
    ],
)
def test_cada_situacao(situacao: str, inicio: str, categoria: str) -> None:
    resultado = textos_de(paragrafos_do_visto(Visto(situacao=situacao), "Chile"))
    assert resultado[0].startswith(inicio)
    assert resultado[1] == f'Categoria: "{categoria}"'


def test_isento_com_rg() -> None:
    resultado = textos_de(paragrafos_do_visto(Visto(aceita_rg=True), "Chile"))
    assert resultado[0].endswith("e a entrada pode ser feita com o RG.")


def test_kosovo_e_malvinas_usam_o_nome_do_territorio() -> None:
    visto = Visto(territorio_nome="Kosovo")
    assert "para Kosovo" in textos_de(paragrafos_do_visto(visto, "Sérvia"))[0]


def test_origem_soberano() -> None:
    visto = Visto(origem="soberano", soberano_nome="França")
    assert (
        "Sem entrada própria na fonte para este território. Vale a entrada do soberano: França."
        in textos_de(paragrafos_do_visto(visto, "Guiana Francesa"))
    )


@pytest.mark.parametrize(
    ("permanencia", "esperado"),
    [
        (Permanencia("padronizada", "90 dias"), "Permanência: 90 dias"),
        (Permanencia("original", "3 months"), "Permanência: 3 months"),
        (
            Permanencia("prazos_divergentes"),
            "Permanência: Prazos divergentes na fonte (ver observações)",
        ),
        (
            Permanencia("varia_conforme_motivo"),
            "Permanência: Varia conforme o motivo (ver observações)",
        ),
    ],
)
def test_os_quatro_tipos_de_permanencia(permanencia: Permanencia, esperado: str) -> None:
    assert esperado in textos_de(paragrafos_do_visto(Visto(permanencia=permanencia), "Chile"))


def test_fonte_sem_licenca_e_sem_data() -> None:
    visto = Visto(fonte=Fonte(licenca=None), dado_de=None)
    assert "Fonte: Wikipédia: Visa (não oficial)." in textos_de(paragrafos_do_visto(visto, "Chile"))


def test_o_link_do_visto_e_so_a_wikipedia() -> None:
    assert urls_de(paragrafos_do_visto(Visto(), "Chile")) == {URL_DA_WIKIPEDIA}


# --------------------------------------------------------------------------- regras gerais
NIVEIS = ("sem_alerta", "evitar", "nao_viajar", "nao_verificado")
SITUACOES = (
    "isento", "visto_na_chegada", "autorizacao_eletronica", "visto_exigido", "outra_situacao",
    "sem_informacao",
)  # fmt: skip


@pytest.mark.parametrize("nivel", NIVEIS)
def test_alerta_sem_palavra_proibida_e_com_fonte_e_data(nivel: str) -> None:
    texto = " ".join(textos_de(paragrafos_do_alerta(Painel(nivel=nivel), Mapa()))).lower()
    assert not [p for p in PROIBIDAS if p in texto]
    assert "fonte:" in texto
    assert "23/10/2026" in texto


@pytest.mark.parametrize("situacao", SITUACOES)
def test_visto_sem_palavra_proibida_e_com_fonte_e_data(situacao: str) -> None:
    texto = " ".join(textos_de(paragrafos_do_visto(Visto(situacao=situacao), "Chile"))).lower()
    assert not [p for p in PROIBIDAS if p in texto]
    assert "fonte:" in texto
    assert "23/10/2026" in texto
