"""Repositórios de vistos: coletas, requisitos, mudanças retidas e itens para revisão."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from farol.dominio.enums import (
    CategoriaDeVisto,
    EstadoDaRetencao,
    EstadoDoItem,
    ResultadoDaColetaDeVistos,
    TipoDeItemParaRevisao,
    TipoTerritorio,
)
from farol.dominio.modelos import (
    ColetaVistos,
    ItemParaRevisao,
    MudancaRetida,
    RequisitoVisto,
    Territorio,
)
from farol.dominio.repositorios import (
    ColetaVistosRepositorio,
    ItemParaRevisaoRepositorio,
    MudancaRetidaRepositorio,
    RequisitoVistoRepositorio,
)

AGORA = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)
HASH = "a" * 64
OUTRO_HASH = "b" * 64

V = ResultadoDaColetaDeVistos


def horas(n: int) -> datetime:
    return AGORA + timedelta(hours=n)


def territorios(sessao: Session, *codigos: str) -> None:
    sessao.add_all(Territorio(codigo=c, nome_pt=c, tipo=TipoTerritorio.PAIS) for c in codigos)
    sessao.flush()


def nova_coleta(
    sessao: Session, resultado: ResultadoDaColetaDeVistos, quando: datetime, **campos: Any
) -> ColetaVistos:
    base: dict[str, Any] = {
        "iniciada_em": quando,
        "finalizada_em": quando,
        "resultado": resultado,
        "motivo": None if resultado is V.VALIDA else "motivo qualquer",
    }
    base.update(campos)
    coleta = ColetaVistos(**base)
    ColetaVistosRepositorio(sessao).adicionar(coleta)
    sessao.flush()
    return coleta


# --------------------------------------------------------------------------- coletas
def test_sem_coletas_nao_ha_ultima(sessao: Session) -> None:
    repositorio = ColetaVistosRepositorio(sessao)
    assert repositorio.ultima_valida() is None
    assert repositorio.ultima_tentativa() is None
    assert repositorio.adiadas_seguidas() == 0
    assert repositorio.falhas_seguidas() == 0


def test_ultima_valida_e_a_de_finalizada_em_mais_recente(sessao: Session) -> None:
    antiga = nova_coleta(sessao, V.VALIDA, horas(-48))
    recente = nova_coleta(sessao, V.VALIDA, horas(-24))
    nova_coleta(sessao, V.REJEITADA, horas(-1))
    assert antiga.id != recente.id
    ultima = ColetaVistosRepositorio(sessao).ultima_valida()
    assert ultima is not None
    assert ultima.id == recente.id


def test_ultima_valida_ignora_o_que_nao_e_valido_e_o_que_ainda_roda(sessao: Session) -> None:
    nova_coleta(sessao, V.REJEITADA, horas(-5))
    nova_coleta(sessao, V.VALIDA, horas(-3), finalizada_em=None)
    assert ColetaVistosRepositorio(sessao).ultima_valida() is None


def test_ultima_tentativa_e_a_mais_recente_de_qualquer_resultado(sessao: Session) -> None:
    nova_coleta(sessao, V.VALIDA, horas(-48))
    ultima = nova_coleta(sessao, V.BLOQUEADA, horas(-2))
    obtida = ColetaVistosRepositorio(sessao).ultima_tentativa()
    assert obtida is not None
    assert obtida.id == ultima.id


def test_adiadas_seguidas_conta_so_o_final_do_historico(sessao: Session) -> None:
    repositorio = ColetaVistosRepositorio(sessao)
    nova_coleta(sessao, V.ADIADA, horas(-10))  # antes de uma válida: não conta
    nova_coleta(sessao, V.VALIDA, horas(-9))
    nova_coleta(sessao, V.ADIADA, horas(-8))
    nova_coleta(sessao, V.ADIADA, horas(-7))
    assert repositorio.adiadas_seguidas() == 2
    assert repositorio.falhas_seguidas() == 0


def test_falhas_seguidas_conta_so_o_final_do_historico(sessao: Session) -> None:
    repositorio = ColetaVistosRepositorio(sessao)
    nova_coleta(sessao, V.FALHOU, horas(-10))
    nova_coleta(sessao, V.ADIADA, horas(-9))  # interrompe a sequência
    nova_coleta(sessao, V.FALHOU, horas(-8))
    nova_coleta(sessao, V.FALHOU, horas(-7))
    nova_coleta(sessao, V.FALHOU, horas(-6))
    assert repositorio.falhas_seguidas() == 3
    assert repositorio.adiadas_seguidas() == 0


def test_sequencias_zeram_quando_a_ultima_tentativa_e_outra(sessao: Session) -> None:
    repositorio = ColetaVistosRepositorio(sessao)
    nova_coleta(sessao, V.ADIADA, horas(-3))
    nova_coleta(sessao, V.FALHOU, horas(-2))
    nova_coleta(sessao, V.BLOQUEADA, horas(-1))
    assert repositorio.adiadas_seguidas() == 0
    assert repositorio.falhas_seguidas() == 0


# --------------------------------------------------------------------------- requisitos
def requisito(coleta_id: int, codigo: str, **campos: Any) -> RequisitoVisto:
    base: dict[str, Any] = {
        "territorio_codigo": codigo,
        "categoria": CategoriaDeVisto.ISENTO,
        "rotulo_original": "Visa not required",
        "linhas_fonte": [{"nome": codigo}],
        "hash_fonte": HASH,
        "lido_em": AGORA,
        "coleta_id": coleta_id,
    }
    base.update(campos)
    return RequisitoVisto(**base)


def test_obter_requisito_por_codigo(sessao: Session) -> None:
    territorios(sessao, "AR", "US")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = RequisitoVistoRepositorio(sessao)
    repositorio.salvar(requisito(coleta.id, "AR"))
    sessao.flush()
    obtido = repositorio.obter("AR")
    assert obtido is not None
    assert obtido.rotulo_original == "Visa not required"
    assert repositorio.obter("US") is None


def test_listar_requisitos_por_lista_de_codigos(sessao: Session) -> None:
    territorios(sessao, "AR", "US", "PE")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = RequisitoVistoRepositorio(sessao)
    for codigo in ("AR", "US", "PE"):
        repositorio.salvar(requisito(coleta.id, codigo))
    sessao.flush()
    assert [r.territorio_codigo for r in repositorio.listar(["US", "AR", "XX"])] == ["AR", "US"]
    assert repositorio.listar([]) == []
    assert [r.territorio_codigo for r in repositorio.listar_todos()] == ["AR", "PE", "US"]


def test_salvar_requisito_novo_e_existente_e_um_upsert(sessao: Session) -> None:
    territorios(sessao, "AR")
    primeira = nova_coleta(sessao, V.VALIDA, horas(-24))
    segunda = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = RequisitoVistoRepositorio(sessao)
    repositorio.salvar(requisito(primeira.id, "AR"))
    sessao.flush()

    salvo = repositorio.salvar(
        requisito(
            segunda.id,
            "AR",
            categoria=CategoriaDeVisto.VISTO_EXIGIDO,
            rotulo_original="Visa required",
            hash_fonte=OUTRO_HASH,
            lido_em=horas(1),
        )
    )
    sessao.flush()
    sessao.expire_all()

    assert [r.territorio_codigo for r in repositorio.listar_todos()] == ["AR"]
    assert salvo.categoria is CategoriaDeVisto.VISTO_EXIGIDO
    obtido = repositorio.obter("AR")
    assert obtido is not None
    assert obtido.hash_fonte == OUTRO_HASH
    assert obtido.coleta_id == segunda.id
    assert obtido.lido_em == horas(1)


# --------------------------------------------------------------------------- mudanças retidas
def retida(coleta_id: int, codigo: str = "AR", **campos: Any) -> MudancaRetida:
    base: dict[str, Any] = {
        "territorio_codigo": codigo,
        "coleta_id": coleta_id,
        "estado": EstadoDaRetencao.PENDENTE,
        "hash_fonte_lido": HASH,
        "candidato": {"categoria": "isento"},
        "categoria_exibida": CategoriaDeVisto.VISTO_EXIGIDO,
        "categoria_lida": CategoriaDeVisto.ISENTO,
        "aceita_rg_exibido": False,
        "aceita_rg_lido": False,
        "criada_em": AGORA,
    }
    base.update(campos)
    return MudancaRetida(**base)


def test_buscar_a_retencao_pendente_e_a_rejeitada_por_territorio(sessao: Session) -> None:
    territorios(sessao, "AR", "US")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    pendente = retida(coleta.id, "AR")
    rejeitada = retida(coleta.id, "AR", estado=EstadoDaRetencao.REJEITADA, hash_fonte_lido="c" * 64)
    repositorio.adicionar(pendente)
    repositorio.adicionar(rejeitada)
    repositorio.adicionar(retida(coleta.id, "US"))
    sessao.flush()

    assert repositorio.pendente_do("AR") is pendente
    assert repositorio.rejeitada_do("AR") is rejeitada
    assert repositorio.rejeitada_do("US") is None
    assert repositorio.pendente_do("PE") is None


def test_listar_pendentes_por_territorio_sem_incluir_as_encerradas(sessao: Session) -> None:
    territorios(sessao, "AR", "US", "PE")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    repositorio.adicionar(retida(coleta.id, "US"))
    repositorio.adicionar(retida(coleta.id, "AR"))
    repositorio.adicionar(retida(coleta.id, "PE", estado=EstadoDaRetencao.CONFIRMADA))
    sessao.flush()
    assert [m.territorio_codigo for m in repositorio.listar_pendentes()] == ["AR", "US"]


def test_atualizar_a_coleta_de_uma_pendente(sessao: Session) -> None:
    territorios(sessao, "AR")
    primeira = nova_coleta(sessao, V.VALIDA, horas(-24))
    segunda = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    pendente = retida(primeira.id)
    repositorio.adicionar(pendente)
    sessao.flush()
    repositorio.atualizar_coleta(pendente, segunda.id)
    sessao.flush()
    assert pendente.coleta_id == segunda.id
    assert pendente.estado is EstadoDaRetencao.PENDENTE


@pytest.mark.parametrize(
    ("transicao", "esperado"),
    [
        ("confirmar", EstadoDaRetencao.CONFIRMADA),
        ("rejeitar", EstadoDaRetencao.REJEITADA),
        ("reverter", EstadoDaRetencao.REVERTIDA),
        ("superar", EstadoDaRetencao.SUPERADA),
    ],
)
def test_transicoes_a_partir_de_pendente(
    sessao: Session, transicao: str, esperado: EstadoDaRetencao
) -> None:
    territorios(sessao, "AR")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    pendente = retida(coleta.id)
    repositorio.adicionar(pendente)
    sessao.flush()

    getattr(repositorio, transicao)(pendente, horas(2))
    sessao.flush()

    assert pendente.estado is esperado
    assert pendente.resolvida_em == horas(2)
    assert repositorio.pendente_do("AR") is None


@pytest.mark.parametrize("transicao", ["reverter", "superar"])
def test_rejeitada_pode_ser_revertida_ou_superada(sessao: Session, transicao: str) -> None:
    territorios(sessao, "AR")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    rejeitada = retida(coleta.id, estado=EstadoDaRetencao.REJEITADA)
    repositorio.adicionar(rejeitada)
    sessao.flush()

    getattr(repositorio, transicao)(rejeitada, horas(2))
    sessao.flush()

    assert rejeitada.estado in (EstadoDaRetencao.REVERTIDA, EstadoDaRetencao.SUPERADA)
    assert repositorio.rejeitada_do("AR") is None


@pytest.mark.parametrize("transicao", ["confirmar", "rejeitar"])
def test_so_a_pendente_pode_ser_confirmada_ou_rejeitada(sessao: Session, transicao: str) -> None:
    territorios(sessao, "AR")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    rejeitada = retida(coleta.id, estado=EstadoDaRetencao.REJEITADA)
    repositorio.adicionar(rejeitada)
    sessao.flush()

    with pytest.raises(ValueError, match="pendente"):
        getattr(repositorio, transicao)(rejeitada, horas(2))
    assert rejeitada.estado is EstadoDaRetencao.REJEITADA
    assert rejeitada.resolvida_em is None


@pytest.mark.parametrize("transicao", ["reverter", "superar"])
def test_retencao_encerrada_nao_muda_de_novo(sessao: Session, transicao: str) -> None:
    territorios(sessao, "AR")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    confirmada = retida(coleta.id, estado=EstadoDaRetencao.CONFIRMADA, resolvida_em=AGORA)
    repositorio.adicionar(confirmada)
    sessao.flush()

    with pytest.raises(ValueError, match="aberta"):
        getattr(repositorio, transicao)(confirmada, horas(2))
    assert confirmada.estado is EstadoDaRetencao.CONFIRMADA


def test_depois_de_encerrar_a_pendente_pode_haver_outra(sessao: Session) -> None:
    territorios(sessao, "AR")
    coleta = nova_coleta(sessao, V.VALIDA, AGORA)
    repositorio = MudancaRetidaRepositorio(sessao)
    primeira = retida(coleta.id)
    repositorio.adicionar(primeira)
    sessao.flush()
    repositorio.superar(primeira, horas(1))
    segunda = retida(coleta.id, hash_fonte_lido=OUTRO_HASH)
    repositorio.adicionar(segunda)
    sessao.flush()
    assert repositorio.pendente_do("AR") is segunda


# --------------------------------------------------------------------------- itens para revisão
NOME = TipoDeItemParaRevisao.NOME
ROTULO = TipoDeItemParaRevisao.ROTULO
REGRA = TipoDeItemParaRevisao.REGRA


def test_registrar_item_novo_fica_pendente(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    contexto = [{"tabela": "principal", "nome_na_fonte": "Narnia"}]
    item = repositorio.registrar_visto(NOME, "narnia", contexto, AGORA)
    sessao.flush()

    assert item.estado is EstadoDoItem.PENDENTE
    assert item.primeira_vez_em == AGORA
    assert item.ultima_vez_em == AGORA
    assert item.contexto == contexto
    assert repositorio.obter(NOME, "narnia") is item
    assert repositorio.obter(ROTULO, "narnia") is None


def test_item_visto_de_novo_atualiza_a_ultima_vez_e_o_contexto(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    repositorio.registrar_visto(NOME, "narnia", [{"nome_na_fonte": "Narnia"}], AGORA)
    sessao.flush()

    de_novo = repositorio.registrar_visto(NOME, "narnia", [{"nome_na_fonte": "Narnia!"}], horas(24))
    sessao.flush()

    assert de_novo.primeira_vez_em == AGORA
    assert de_novo.ultima_vez_em == horas(24)
    assert de_novo.contexto == [{"nome_na_fonte": "Narnia!"}]
    assert de_novo.estado is EstadoDoItem.PENDENTE
    assert len(repositorio.listar_pendentes()) == 1


def test_item_resolvido_que_reaparece_volta_a_pendente(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    repositorio.registrar_visto(ROTULO, "visa on arrival", [], AGORA)
    sessao.flush()
    repositorio.resolver_nao_vistos(horas(24), horas(24))
    sessao.flush()
    resolvido = repositorio.obter(ROTULO, "visa on arrival")
    assert resolvido is not None
    assert resolvido.estado is EstadoDoItem.RESOLVIDO

    de_novo = repositorio.registrar_visto(ROTULO, "visa on arrival", [], horas(48))
    sessao.flush()

    assert de_novo.estado is EstadoDoItem.PENDENTE
    assert de_novo.resolvido_em is None
    assert de_novo.ultima_vez_em == horas(48)


def test_item_ignorado_nao_volta(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item = repositorio.registrar_visto(NOME, "narnia", [], AGORA)
    repositorio.ignorar_nome(item, "lugar imaginário", horas(1))
    sessao.flush()

    de_novo = repositorio.registrar_visto(NOME, "narnia", [], horas(24))
    sessao.flush()

    assert de_novo.estado is EstadoDoItem.IGNORADO
    assert de_novo.motivo_ignorar == "lugar imaginário"
    assert repositorio.listar_pendentes() == []


def test_resolver_os_nao_vistos_na_coleta(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    repositorio.registrar_visto(NOME, "sumiu", [], AGORA)
    repositorio.registrar_visto(NOME, "continua", [], AGORA)
    repositorio.registrar_visto(REGRA, "JM", {"hash_lido": HASH}, AGORA)
    sessao.flush()

    # Na coleta seguinte, só "continua" foi visto
    repositorio.registrar_visto(NOME, "continua", [], horas(24))
    resolvidos = repositorio.resolver_nao_vistos(horas(24), horas(25))
    sessao.flush()

    assert resolvidos == 2
    sumiu = repositorio.obter(NOME, "sumiu")
    regra = repositorio.obter(REGRA, "JM")
    continua = repositorio.obter(NOME, "continua")
    assert sumiu is not None
    assert regra is not None
    assert continua is not None
    assert sumiu.estado is EstadoDoItem.RESOLVIDO
    assert sumiu.resolvido_em == horas(25)
    assert regra.estado is EstadoDoItem.RESOLVIDO
    assert continua.estado is EstadoDoItem.PENDENTE
    assert continua.resolvido_em is None


def test_resolver_os_nao_vistos_nao_toca_nos_ignorados(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item = repositorio.registrar_visto(NOME, "narnia", [], AGORA)
    repositorio.ignorar_nome(item, "lugar imaginário", AGORA)
    sessao.flush()
    assert repositorio.resolver_nao_vistos(horas(24), horas(24)) == 0
    assert item.estado is EstadoDoItem.IGNORADO


def test_listar_pendentes_com_e_sem_filtro_de_tipo(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    repositorio.registrar_visto(ROTULO, "b-rotulo", [], AGORA)
    repositorio.registrar_visto(NOME, "a-nome", [], AGORA)
    repositorio.registrar_visto(REGRA, "ZM", {}, AGORA)
    resolvido = repositorio.registrar_visto(NOME, "z-resolvido", [], AGORA)
    sessao.flush()
    resolvido.estado = EstadoDoItem.RESOLVIDO
    resolvido.resolvido_em = AGORA
    sessao.flush()

    assert [(i.tipo, i.valor) for i in repositorio.listar_pendentes()] == [
        (NOME, "a-nome"),
        (REGRA, "ZM"),
        (ROTULO, "b-rotulo"),
    ]
    assert [i.valor for i in repositorio.listar_pendentes(ROTULO)] == ["b-rotulo"]


def test_ignorar_nome_grava_estado_motivo_e_data(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item = repositorio.registrar_visto(NOME, "narnia", [], AGORA)
    repositorio.ignorar_nome(item, "  lugar imaginário  ", horas(3))
    sessao.flush()
    assert item.estado is EstadoDoItem.IGNORADO
    assert item.motivo_ignorar == "lugar imaginário"
    assert item.resolvido_em == horas(3)


@pytest.mark.parametrize("motivo", ["", "   "])
def test_ignorar_nome_exige_motivo(sessao: Session, motivo: str) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item = repositorio.registrar_visto(NOME, "narnia", [], AGORA)
    with pytest.raises(ValueError, match="motivo"):
        repositorio.ignorar_nome(item, motivo, AGORA)
    assert item.estado is EstadoDoItem.PENDENTE


@pytest.mark.parametrize("tipo", [ROTULO, REGRA])
def test_rotulo_e_regra_nao_podem_ser_ignorados(
    sessao: Session, tipo: TipoDeItemParaRevisao
) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item = repositorio.registrar_visto(tipo, "x", [], AGORA)
    with pytest.raises(ValueError, match="nome"):
        repositorio.ignorar_nome(item, "motivo", AGORA)
    assert item.estado is EstadoDoItem.PENDENTE


def test_so_nome_pendente_pode_ser_ignorado(sessao: Session) -> None:
    repositorio = ItemParaRevisaoRepositorio(sessao)
    item: ItemParaRevisao = repositorio.registrar_visto(NOME, "narnia", [], AGORA)
    repositorio.ignorar_nome(item, "primeiro motivo", AGORA)
    with pytest.raises(ValueError, match="pendente"):
        repositorio.ignorar_nome(item, "segundo motivo", horas(1))
    assert item.motivo_ignorar == "primeiro motivo"
