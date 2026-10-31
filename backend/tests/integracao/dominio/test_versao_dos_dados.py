"""Versão dos dados: sobe a cada escrita confirmada por qualquer job ou comando, e só nelas."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import Engine, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from farol.coleta import ServicoDeColetaDeAlertas
from farol.dominio import (
    Alerta,
    EstadoDoItem,
    ExecucaoColeta,
    ItemParaRevisao,
    TipoDeItemParaRevisao,
    TipoExecucao,
)
from farol.infra import abrir_sessao, criar_fabrica_de_sessoes, ler_versao_dos_dados
from farol.vistos import ServicoDoDono
from farol.vistos.normalizacao import chave_de_consulta

if TYPE_CHECKING:
    from tests.conftest import GovBrFalso, RelogioFalso

AGORA = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
TABELAS_ESCRITAS = "alerta, execucao_coleta, item_para_revisao, classificacao, nivel_territorio"


@pytest.fixture
def fabrica(engine_teste: Engine) -> Iterator[sessionmaker[Session]]:
    """Sessões que confirmam de verdade; apaga o que os testes gravaram ao final."""
    yield criar_fabrica_de_sessoes(engine_teste)
    with engine_teste.begin() as conexao:
        conexao.execute(text(f"TRUNCATE {TABELAS_ESCRITAS} RESTART IDENTITY CASCADE"))


def versao(fabrica: sessionmaker[Session]) -> int:
    with abrir_sessao(fabrica) as sessao:
        return ler_versao_dos_dados(sessao)


def nova_execucao() -> ExecucaoColeta:
    return ExecucaoColeta(tipo=TipoExecucao.ALERTAS, iniciada_em=AGORA)


def test_a_migracao_cria_o_contador_em_zero_ou_mais(fabrica: sessionmaker[Session]) -> None:
    assert versao(fabrica) >= 0


def test_so_ler_nao_sobe_a_versao(fabrica: sessionmaker[Session]) -> None:
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.scalars(select(Alerta)).all()
    assert versao(fabrica) == antes


def test_gravar_objetos_sobe_a_versao_uma_vez(fabrica: sessionmaker[Session]) -> None:
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.add_all([nova_execucao(), nova_execucao(), nova_execucao()])
    assert versao(fabrica) == antes + 1


def test_alterar_um_objeto_sobe_a_versao(fabrica: sessionmaker[Session]) -> None:
    with abrir_sessao(fabrica) as sessao:
        execucao = nova_execucao()
        sessao.add(execucao)
        sessao.flush()
        codigo = execucao.id
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.get_one(ExecucaoColeta, codigo).completa = True
    assert versao(fabrica) == antes + 1


def test_apagar_um_objeto_sobe_a_versao(fabrica: sessionmaker[Session]) -> None:
    with abrir_sessao(fabrica) as sessao:
        execucao = nova_execucao()
        sessao.add(execucao)
        sessao.flush()
        codigo = execucao.id
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.delete(sessao.get_one(ExecucaoColeta, codigo))
    assert versao(fabrica) == antes + 1


def test_update_em_massa_sobe_a_versao(fabrica: sessionmaker[Session]) -> None:
    with abrir_sessao(fabrica) as sessao:
        sessao.add(nova_execucao())
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.execute(update(ExecucaoColeta).values(completa=True))
    assert versao(fabrica) == antes + 1


def test_transacao_desfeita_nao_sobe_a_versao(fabrica: sessionmaker[Session]) -> None:
    antes = versao(fabrica)
    with pytest.raises(RuntimeError), abrir_sessao(fabrica) as sessao:
        sessao.add(nova_execucao())
        sessao.flush()
        raise RuntimeError("falhou no meio")
    assert versao(fabrica) == antes


def test_a_marca_de_uma_sessao_nao_vaza_para_a_seguinte(fabrica: sessionmaker[Session]) -> None:
    with abrir_sessao(fabrica) as sessao:
        sessao.add(nova_execucao())
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        sessao.scalars(select(ExecucaoColeta)).all()
    assert versao(fabrica) == antes


def test_a_coleta_de_alertas_sobe_a_versao(
    fabrica: sessionmaker[Session], govbr: "GovBrFalso", relogio: "RelogioFalso"
) -> None:
    govbr.publicar_alertas(2)
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        ServicoDeColetaDeAlertas(
            sessao, govbr, relogio, url_da_lista="https://www.gov.br/mre/alertas"
        ).coletar()
    assert versao(fabrica) > antes


def test_um_comando_do_dono_sobe_a_versao(
    fabrica: sessionmaker[Session], relogio: "RelogioFalso"
) -> None:
    with abrir_sessao(fabrica) as sessao:
        sessao.add(
            ItemParaRevisao(
                tipo=TipoDeItemParaRevisao.NOME,
                valor=chave_de_consulta("Atlantis"),
                contexto=[],
                primeira_vez_em=AGORA,
                ultima_vez_em=AGORA,
                estado=EstadoDoItem.PENDENTE,
            )
        )
    antes = versao(fabrica)
    with abrir_sessao(fabrica) as sessao:
        ServicoDoDono(sessao, relogio).ignorar_nome("Atlantis", "não é um país")
    assert versao(fabrica) == antes + 1
