"""Montador da resposta: citações, "Ver trecho" e avisos vêm do código, nunca do modelo."""

from datetime import UTC, datetime

from farol.chat.ferramentas import TrechoUsado
from farol.chat.montador import (
    NAO_ENCONTREI,
    SEM_DADOS,
    TEXTO_DA_CONTINGENCIA,
    montar_contingencia,
    montar_pergunta_de_volta,
    montar_resposta,
    montar_sem_dados,
)

TEXTO = "O Ministério recomenda não viajar para o Irã. Dirija-se ao abrigo mais próximo."


def usado(
    alerta_id: int = 1, inicio: int = 0, fim: int = 45, vigor: str = "em_vigor"
) -> TrechoUsado:
    return TrechoUsado(
        alerta_id=alerta_id,
        titulo=f"Alerta {alerta_id}",
        data=datetime(2026, 10, 5, tzinfo=UTC),
        url=f"https://www.gov.br/mre/a{alerta_id}",
        vigor=vigor,  # type: ignore[arg-type]
        inicio=inicio,
        fim=fim,
        trecho=TEXTO[inicio:fim],
    )


def test_citacao_de_alerta_com_titulo_data_link_vigor_e_trecho_original() -> None:
    resposta = montar_resposta("resposta", "O Itamaraty recomenda não viajar.", [usado()])

    assert resposta.situacao == "resposta"
    assert resposta.texto == "O Itamaraty recomenda não viajar."
    [citacao] = resposta.citacoes
    assert citacao.tipo == "alerta"
    assert citacao.titulo == "Alerta 1"
    assert citacao.data == datetime(2026, 10, 5, tzinfo=UTC)
    assert citacao.url == "https://www.gov.br/mre/a1"
    assert citacao.vigor == "em_vigor"
    assert citacao.trecho == TEXTO[0:45]  # caractere a caractere
    assert citacao.licenca is None
    assert resposta.cartoes == ()


def test_o_mesmo_trecho_citado_duas_vezes_aparece_uma_vez() -> None:
    resposta = montar_resposta("resposta", "texto", [usado(), usado(), usado(1, 45, 80)])
    assert [(c.trecho) for c in resposta.citacoes] == [TEXTO[0:45], TEXTO[45:80]]


def test_alerta_anterior_ganha_aviso_do_sistema() -> None:
    resposta = montar_resposta("resposta", "texto", [usado(vigor="anterior")])
    assert resposta.citacoes[0].vigor == "anterior"
    assert any("anterior" in aviso for aviso in resposta.avisos)


def test_sem_alerta_anterior_nao_ha_aviso() -> None:
    assert montar_resposta("resposta", "texto", [usado()]).avisos == ()


def test_resposta_sem_nenhum_trecho_vira_nao_encontrei() -> None:
    """O modelo não pode afirmar nada sobre os alertas sem ter um trecho para mostrar."""
    resposta = montar_resposta("resposta", "O Irã exige visto de turista.", [])
    assert resposta.situacao == "nao_encontrei"
    assert resposta.texto == NAO_ENCONTREI
    assert resposta.citacoes == ()


def test_nao_encontrei_aponta_o_painel_e_o_portal_consular_sem_link() -> None:
    resposta = montar_resposta("nao_encontrei", "qualquer coisa do modelo", [usado()])
    assert resposta.situacao == "nao_encontrei"
    assert resposta.texto == NAO_ENCONTREI
    assert "painel" in NAO_ENCONTREI and "Portal Consular" in NAO_ENCONTREI
    assert "http" not in NAO_ENCONTREI
    assert resposta.citacoes == ()  # trechos que não responderam não viram citação


def test_recusa_fica_com_o_texto_e_sem_citacoes() -> None:
    resposta = montar_resposta("recusa", "Só respondo sobre viagens e alertas.", [usado()])
    assert resposta.situacao == "recusa" and resposta.citacoes == ()


def test_links_so_existem_nas_citacoes() -> None:
    resposta = montar_resposta("resposta", "texto", [usado(1), usado(2)])
    assert [c.url for c in resposta.citacoes] == [
        "https://www.gov.br/mre/a1",
        "https://www.gov.br/mre/a2",
    ]
    assert "http" not in resposta.texto


def test_pergunta_de_volta() -> None:
    resposta = montar_pergunta_de_volta("De qual país?")
    assert (resposta.situacao, resposta.texto, resposta.citacoes) == (
        "pergunta_de_volta",
        "De qual país?",
        (),
    )


def test_sem_dados_ainda() -> None:
    resposta = montar_sem_dados()
    assert resposta.situacao == "nao_encontrei" and resposta.texto == SEM_DADOS
    assert "ainda não há dados" in SEM_DADOS.lower()


def test_contingencia_mostra_os_trechos_com_texto_fixo_do_sistema() -> None:
    resposta = montar_contingencia([usado(), usado(vigor="anterior")])
    assert resposta.situacao == "so_registros"
    assert resposta.texto == TEXTO_DA_CONTINGENCIA
    assert len(resposta.citacoes) == 1  # o mesmo trecho, uma vez
    assert resposta.avisos == ()  # o que ficou é o trecho em vigor


def test_contingencia_sem_trechos_vira_nao_encontrei() -> None:
    resposta = montar_contingencia([])
    assert resposta.situacao == "nao_encontrei" and resposta.texto == NAO_ENCONTREI
