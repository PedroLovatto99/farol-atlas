"""Serviço de coleta de alertas: hash, execução, completude, remoção e confirmação (FR-040)."""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from farol.coleta import ServicoDeColetaDeAlertas, hash_do_alerta
from farol.dominio import Alerta, ExecucaoColeta, TipoExecucao
from farol.infra import Pagina

if TYPE_CHECKING:
    from tests.conftest import GovBrFalso, RelogioFalso

URL_DA_LISTA = "https://www.gov.br/mre/alertas"


def servico(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> ServicoDeColetaDeAlertas:
    return ServicoDeColetaDeAlertas(sessao, govbr, relogio, url_da_lista=URL_DA_LISTA)


def alerta(sessao: Session, url: str) -> Alerta:
    return sessao.scalars(select(Alerta).where(Alerta.url == url)).one()


def todos(sessao: Session) -> list[Alerta]:
    return list(sessao.scalars(select(Alerta).order_by(Alerta.id)))


def execucoes(sessao: Session) -> list[ExecucaoColeta]:
    return list(sessao.scalars(select(ExecucaoColeta).order_by(ExecucaoColeta.id)))


# --------------------------------------------------------------------------- hash
def test_hash_e_sha256_de_titulo_e_texto_com_espacos_normalizados() -> None:
    esperado = hashlib.sha256(b"Alerta X\nO texto do alerta.").hexdigest()
    assert hash_do_alerta("Alerta X", "O texto do alerta.") == esperado
    assert hash_do_alerta("  Alerta   X ", "O  texto\n do alerta. ") == esperado
    assert len(esperado) == 64


def test_hash_muda_quando_o_titulo_ou_o_texto_mudam() -> None:
    base = hash_do_alerta("Alerta X", "Texto")
    assert hash_do_alerta("Alerta Y", "Texto") != base
    assert hash_do_alerta("Alerta X", "Outro texto") != base


# --------------------------------------------------------------------------- coleta completa
def test_coleta_completa_grava_alertas_e_confirma(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.completa
    assert resultado.paginas_esperadas == 10
    assert resultado.paginas_lidas == 10
    assert len(todos(sessao)) == 10

    primeiro = alerta(sessao, urls[0])
    assert primeiro.titulo == "Alerta 0"
    assert primeiro.texto == "Texto do alerta 0."
    assert primeiro.html_corpo is not None
    assert primeiro.pagina_lida is True
    assert primeiro.hash == hash_do_alerta("Alerta 0", "Texto do alerta 0.")
    assert primeiro.primeira_coleta_em == relogio.agora()
    assert primeiro.removido_em is None

    [execucao] = execucoes(sessao)
    assert execucao.tipo is TipoExecucao.ALERTAS
    assert execucao.iniciada_em == relogio.agora()
    assert execucao.finalizada_em is not None
    assert execucao.paginas_esperadas == 10
    assert execucao.paginas_lidas == 10
    assert execucao.lista_lida_inteira is True
    assert execucao.completa is True
    assert execucao.motivo_interrupcao is None
    assert resultado.execucao_id == execucao.id


def test_execucao_completa_confirma_todos_os_alertas_da_lista(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.publicar_alertas(5)
    servico(sessao, govbr, relogio).coletar()
    [execucao] = execucoes(sessao)
    for item in todos(sessao):
        assert item.confirmado_execucao_id == execucao.id
        assert item.confirmado_hash == item.hash
        assert item.confirmado_titulo == item.titulo
        assert item.confirmado_data_ref == (item.modificado_em or item.publicado_em)


def test_data_de_referencia_e_a_modificacao_quando_existe(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    [url] = govbr.publicar_alertas(1)
    publicado = datetime(2026, 7, 4, 13, 10, tzinfo=UTC)
    modificado = datetime(2026, 8, 17, 19, 23, tzinfo=UTC)
    govbr.publicar_pagina(url, "Alerta 0", "Texto", publicado, modificado)
    servico(sessao, govbr, relogio).coletar()
    item = alerta(sessao, url)
    assert item.modificado_em == modificado
    assert item.confirmado_data_ref == modificado


# --------------------------------------------------------------------------- novo, alterado, igual
def test_so_novo_ou_alterado_segue_para_classificacao(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(3)
    primeira = servico(sessao, govbr, relogio).coletar()
    assert len(primeira.para_classificar) == 3

    relogio.avancar(days=1)
    segunda = servico(sessao, govbr, relogio).coletar()
    assert segunda.para_classificar == ()  # nada mudou

    relogio.avancar(days=1)
    publicado = datetime(2026, 6, 2, 15, 0, tzinfo=UTC)
    govbr.publicar_pagina(urls[1], "Alerta 1", "Texto NOVO do alerta 1.", publicado)
    [novo] = govbr.publicar_alertas(1, a_partir_de=3)
    terceira = servico(sessao, govbr, relogio).coletar()
    assert set(terceira.para_classificar) == {alerta(sessao, urls[1]).id, alerta(sessao, novo).id}
    assert alerta(sessao, urls[1]).texto == "Texto NOVO do alerta 1."


def test_reler_um_alerta_igual_so_atualiza_a_ultima_coleta(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    [url] = govbr.publicar_alertas(1)
    servico(sessao, govbr, relogio).coletar()
    primeira_vez = relogio.agora()
    relogio.avancar(days=2)
    servico(sessao, govbr, relogio).coletar()
    item = alerta(sessao, url)
    assert item.primeira_coleta_em == primeira_vez
    assert item.ultima_coleta_em == relogio.agora()


# --------------------------------------------------------------------------- remoção
def test_remocao_so_acontece_em_coleta_completa(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    servico(sessao, govbr, relogio).coletar()

    # coleta incompleta (5 de 9 páginas lidas): o alerta que sumiu da lista NÃO é removido
    relogio.avancar(days=1)
    govbr.remover_da_lista(urls[0])
    for url in urls[1:5]:
        govbr.falhar(url)
    incompleta = servico(sessao, govbr, relogio).coletar()
    assert not incompleta.completa
    assert alerta(sessao, urls[0]).removido_em is None

    # coleta completa: agora o alerta que sumiu é marcado como removido
    relogio.avancar(days=1)
    govbr.restaurar(*urls[1:5])
    completa = servico(sessao, govbr, relogio).coletar()
    assert completa.completa
    assert alerta(sessao, urls[0]).removido_em == relogio.agora()
    assert completa.removidos == 1


def test_alerta_que_volta_para_a_lista_limpa_a_remocao(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(4)
    servico(sessao, govbr, relogio).coletar()

    sumido = govbr.itens[0]
    govbr.remover_da_lista(urls[0])
    relogio.avancar(days=1)
    servico(sessao, govbr, relogio).coletar()
    assert alerta(sessao, urls[0]).removido_em is not None

    govbr.itens.insert(0, sumido)
    govbr.publicar_lista()
    relogio.avancar(days=1)
    servico(sessao, govbr, relogio).coletar()
    assert alerta(sessao, urls[0]).removido_em is None


# ------------------------------------------------------------------ limites de páginas lidas
@pytest.mark.parametrize(("lidas", "completa"), [(69, False), (70, True), (100, True)])
def test_limite_de_70_por_cento_das_paginas(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso", lidas: int, completa: bool
) -> None:
    urls = govbr.publicar_alertas(100)
    for url in urls[lidas:]:
        govbr.falhar(url)

    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.paginas_esperadas == 100
    assert resultado.paginas_lidas == lidas
    assert resultado.completa is completa
    [execucao] = execucoes(sessao)
    assert execucao.completa is completa
    assert execucao.lista_lida_inteira is True  # a lista foi lida inteira; faltaram páginas


# --------------------------------------------------------------------------- próxima página
def test_segue_o_link_de_proxima_pagina_ate_acabar(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.publicar_alertas(4)
    pagina_2 = f"{URL_DA_LISTA}?b_start:int=20"
    itens = list(govbr.itens)
    # 1ª página: alertas 0 e 1 e o link; 2ª página: alertas 2 e 3 e nenhum link
    govbr.paginas[URL_DA_LISTA] = Pagina(
        URL_DA_LISTA, 200, govbr.html_da_lista(itens[:2], pagina_2), None
    )
    govbr.paginas[pagina_2] = Pagina(pagina_2, 200, govbr.html_da_lista(itens[2:]), None)

    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.completa
    assert resultado.paginas_esperadas == 4
    assert len(todos(sessao)) == 4
    assert pagina_2 in govbr.pedidos


def test_link_de_proxima_pagina_que_falha_deixa_a_coleta_incompleta(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.publicar_alertas(5)  # todas as páginas dos alertas estão ótimas
    pagina_2 = f"{URL_DA_LISTA}?b_start:int=20"
    govbr.publicar_lista(proxima=pagina_2)
    govbr.falhar(pagina_2, "HTTP 500")

    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.paginas_lidas == 5  # os 5 alertas da 1ª página foram lidos
    assert not resultado.completa
    [execucao] = execucoes(sessao)
    assert execucao.lista_lida_inteira is False
    assert execucao.completa is False
    assert execucao.motivo_interrupcao is not None
    assert "próxima página" in execucao.motivo_interrupcao
    # e nada foi confirmado
    assert all(item.confirmado_execucao_id is None for item in todos(sessao))


# --------------------------------------------------------------------------- lista com problema
def test_falha_ao_baixar_a_lista_registra_a_execucao_incompleta(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.falhar(URL_DA_LISTA, "HTTP 503")
    resultado = servico(sessao, govbr, relogio).coletar()
    assert not resultado.completa
    [execucao] = execucoes(sessao)
    assert execucao.finalizada_em is not None
    assert execucao.lista_lida_inteira is False
    assert execucao.motivo_interrupcao is not None
    assert "HTTP 503" in execucao.motivo_interrupcao
    assert todos(sessao) == []


def test_lista_sem_nenhum_item_e_incompleta(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.publicar_lista()  # lista vazia
    resultado = servico(sessao, govbr, relogio).coletar()
    assert not resultado.completa
    [execucao] = execucoes(sessao)
    assert execucao.motivo_interrupcao is not None
    assert "formato" in execucao.motivo_interrupcao


# --------------------------------------------------------------------------- verificação humana
def test_verificacao_humana_interrompe_e_grava_o_motivo(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    govbr.falhar(urls[2], "caiu na verificação humana")

    resultado = servico(sessao, govbr, relogio).coletar()

    assert not resultado.completa
    assert resultado.paginas_lidas == 2
    assert urls[3] not in govbr.pedidos  # nunca insiste
    [execucao] = execucoes(sessao)
    assert execucao.motivo_interrupcao == "caiu na verificação humana"
    assert execucao.completa is False
    assert execucao.finalizada_em is not None


def test_bloqueio_depois_de_ler_mais_de_70_por_cento_continua_incompleto(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    govbr.falhar(urls[8], "bloqueado (HTTP 429)")  # 8 lidas (80%), depois o bloqueio
    resultado = servico(sessao, govbr, relogio).coletar()
    assert resultado.paginas_lidas == 8
    assert not resultado.completa  # quem foi bloqueado não confirma nada
    assert all(item.confirmado_execucao_id is None for item in todos(sessao))


# --------------------------------------------------------------------------- página não lida
def test_alerta_novo_com_pagina_nao_lida_fica_so_com_o_que_a_lista_informa(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    govbr.falhar(urls[4])

    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.completa  # 9 de 10
    sem_pagina = alerta(sessao, urls[4])
    assert sem_pagina.pagina_lida is False
    assert sem_pagina.texto is None
    assert sem_pagina.html_corpo is None
    assert sem_pagina.hash is None
    assert sem_pagina.titulo == "Alerta 4"
    # a lista só traz o dia (05/06/2026): meia-noite em Brasília
    meia_noite = datetime(2026, 6, 5, 3, 0, tzinfo=UTC)
    assert sem_pagina.publicado_em == meia_noite
    # a execução completa o confirma, mas sem hash: ficará pendente (FR-008)
    [execucao] = execucoes(sessao)
    assert sem_pagina.confirmado_execucao_id == execucao.id
    assert sem_pagina.confirmado_hash is None
    assert sem_pagina.confirmado_titulo == "Alerta 4"
    assert sem_pagina.confirmado_data_ref == meia_noite
    assert sem_pagina.id not in resultado.para_classificar


def test_alerta_conhecido_com_pagina_nao_lida_mantem_o_que_estava_confirmado(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    servico(sessao, govbr, relogio).coletar()
    antes = alerta(sessao, urls[4])
    hash_confirmado = antes.confirmado_hash
    assert hash_confirmado is not None

    relogio.avancar(days=1)
    govbr.falhar(urls[4])
    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.completa
    depois = alerta(sessao, urls[4])
    assert depois.pagina_lida is True  # continua com o conteúdo já conhecido
    assert depois.hash == hash_confirmado
    assert depois.confirmado_hash == hash_confirmado  # FR-008a: o nível não muda
    assert depois.confirmado_execucao_id == resultado.execucao_id
    assert depois.confirmado_titulo == "Alerta 4"


def test_alerta_conhecido_cuja_data_mudou_e_nao_foi_lido_vira_pendente(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    servico(sessao, govbr, relogio).coletar()

    relogio.avancar(days=1)
    nova_data = datetime(2026, 9, 9, 15, 0, tzinfo=UTC)
    govbr.itens[4] = (govbr.itens[4][0], urls[4], nova_data)
    govbr.publicar_lista()
    govbr.falhar(urls[4])
    resultado = servico(sessao, govbr, relogio).coletar()

    assert resultado.completa
    mudado = alerta(sessao, urls[4])
    assert mudado.confirmado_execucao_id == resultado.execucao_id
    assert mudado.confirmado_hash is None  # mudou e não foi lido: pendente
    assert mudado.confirmado_data_ref == datetime(2026, 9, 9, 3, 0, tzinfo=UTC)  # dia da lista


# ------------------------------------------------------------------ coleta incompleta não confirma
def test_alerta_novo_ou_alterado_lido_em_coleta_incompleta_nao_e_confirmado(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    servico(sessao, govbr, relogio).coletar()
    [execucao_1] = execucoes(sessao)
    antes = alerta(sessao, urls[0])
    confirmado_antes = (
        antes.confirmado_execucao_id,
        antes.confirmado_hash,
        antes.confirmado_titulo,
        antes.confirmado_data_ref,
    )

    # 2ª coleta: o alerta 0 mudou e foi lido, aparece um alerta novo, mas só 4 de 11 páginas vêm
    relogio.avancar(days=1)
    publicado = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
    govbr.publicar_pagina(urls[0], "Alerta 0", "Texto ALTERADO.", publicado)
    [novo] = govbr.publicar_alertas(1, a_partir_de=10)
    for url in urls[3:]:
        govbr.falhar(url)

    resultado = servico(sessao, govbr, relogio).coletar()

    assert not resultado.completa
    assert resultado.execucao_id != execucao_1.id
    alterado = alerta(sessao, urls[0])
    assert alterado.texto == "Texto ALTERADO."  # a leitura fica guardada...
    assert alterado.hash == hash_do_alerta("Alerta 0", "Texto ALTERADO.")
    assert (  # ...mas o que estava confirmado continua igual
        alterado.confirmado_execucao_id,
        alterado.confirmado_hash,
        alterado.confirmado_titulo,
        alterado.confirmado_data_ref,
    ) == confirmado_antes
    criado = alerta(sessao, novo)
    assert criado.pagina_lida is True
    assert criado.confirmado_execucao_id is None
    assert criado.confirmado_hash is None


def test_a_proxima_coleta_completa_confirma_o_que_a_incompleta_leu(
    sessao: Session, govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    urls = govbr.publicar_alertas(10)
    servico(sessao, govbr, relogio).coletar()

    relogio.avancar(days=1)
    publicado = datetime(2026, 6, 1, 18, 0, tzinfo=UTC)
    govbr.publicar_pagina(urls[0], "Alerta 0", "Texto ALTERADO.", publicado)
    for url in urls[3:]:
        govbr.falhar(url)
    servico(sessao, govbr, relogio).coletar()  # incompleta

    relogio.avancar(days=1)
    govbr.restaurar(*urls[3:])
    completa = servico(sessao, govbr, relogio).coletar()

    assert completa.completa
    confirmado = alerta(sessao, urls[0])
    assert confirmado.confirmado_hash == hash_do_alerta("Alerta 0", "Texto ALTERADO.")
    assert confirmado.confirmado_execucao_id == completa.execucao_id
