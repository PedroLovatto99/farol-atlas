"""Retenção por país e itens para revisão, ponta a ponta (spec 002, cenários 12a a 12h; FR-010a)."""

import hashlib
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from farol.dominio import (
    CategoriaDeVisto,
    EstadoDaRetencao,
    EstadoDoItem,
    ItemParaRevisaoRepositorio,
    MotivoOutraSituacao,
    MudancaRetidaRepositorio,
    TipoDeItemParaRevisao,
)
from farol.vistos import Dicionario, dicionario_padrao
from farol.vistos.fonte import TABELA_PRINCIPAL, LinhaDaFonte

if TYPE_CHECKING:
    from tests.integracao.vistos.conftest import Cenario

ISENTO = CategoriaDeVisto.ISENTO
NA_CHEGADA = CategoriaDeVisto.VISTO_NA_CHEGADA
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO
PENDENTE = EstadoDaRetencao.PENDENTE
REJEITADA = EstadoDaRetencao.REJEITADA
REVERTIDA = EstadoDaRetencao.REVERTIDA
SUPERADA = EstadoDaRetencao.SUPERADA
LOG = "farol.vistos"


def primeira_coleta(cenario: "Cenario") -> None:
    """A primeira coleta válida e, depois dela, uma semana de intervalo."""
    assert cenario.coletar().valida
    cenario.semana_seguinte()


def nome_novo(nome: str = "Atlantis", rotulo: str = "Visa not required") -> LinhaDaFonte:
    return LinhaDaFonte(TABELA_PRINCIPAL, None, nome, rotulo, "", "")


# --------------------------------------------------------------------------- 12a e 12b
def test_mudanca_para_menos_exigente_fica_retida_mesmo_com_um_pais_so(
    cenario: "Cenario",
) -> None:  # 12a e 12b
    primeira = cenario.coletar()
    data_antiga = cenario.relogio.agora()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required", permanencia="90 days")

    resumo = cenario.coletar()

    assert resumo.valida
    assert (resumo.aplicadas, resumo.sem_mudanca) == (0, 227)
    [retida] = resumo.retidas
    assert (retida.codigo, retida.categoria_exibida, retida.categoria_lida) == (
        "DZ",
        EXIGIDO,
        ISENTO,
    )
    assert (retida.aceita_rg_exibido, retida.aceita_rg_lido) == (False, False)

    # o país mantém todos os dados anteriores, com a data deles
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert argelia.rotulo_original == "Visa required"
    assert argelia.permanencia_tipo == "nenhuma"
    assert argelia.lido_em == data_antiga
    assert argelia.coleta_id == primeira.coleta_id

    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is PENDENTE
    assert (mudanca.categoria_exibida, mudanca.categoria_lida) == (EXIGIDO, ISENTO)
    assert mudanca.coleta_id == resumo.coleta_id
    assert mudanca.criada_em == cenario.relogio.agora()
    assert mudanca.resolvida_em is None
    assert len(mudanca.hash_fonte_lido) == 64
    assert mudanca.candidato["categoria"] == "isento"
    assert mudanca.candidato["permanencia_texto"] == "90 dias"
    assert mudanca.candidato["hash_fonte"] == mudanca.hash_fonte_lido
    assert cenario.coletas()[-1].retidas == 1


def test_retidos_ate_10_por_cento_nao_avisam_de_vandalismo(
    cenario: "Cenario", caplog: pytest.LogCaptureFixture
) -> None:
    primeira_coleta(cenario)
    cenario.editar("Algeria", rotulo="Visa not required")
    with caplog.at_level(logging.INFO, logger=LOG):
        cenario.coletar()
    assert not [r for r in caplog.records if "vandalismo" in r.getMessage()]


def nomes_nao_isentos(cenario: "Cenario", quantos: int) -> list[str]:
    dicionario = dicionario_padrao()
    vistos: set[str | None] = set()
    escolhidos: list[str] = []
    for linha in cenario.linhas:
        codigo = dicionario.ligar_nome(linha.nome).codigo
        if (
            linha.tabela == TABELA_PRINCIPAL
            and linha.rotulo != "Visa not required"
            and linha.rotulo != "Freedom of Movement"
            and codigo not in vistos
        ):
            vistos.add(codigo)
            escolhidos.append(linha.nome)
    return escolhidos[:quantos]


@pytest.mark.parametrize(("quantos", "avisa"), [(22, False), (23, True)])
def test_retidos_acima_de_10_por_cento_dos_reconhecidos_avisam_de_vandalismo_em_massa(
    cenario: "Cenario", caplog: pytest.LogCaptureFixture, quantos: int, avisa: bool
) -> None:
    primeira_coleta(cenario)
    for nome in nomes_nao_isentos(cenario, quantos):
        cenario.editar(nome, rotulo="Visa not required")  # 10% de 228 são 22,8

    with caplog.at_level(logging.INFO, logger=LOG):
        resumo = cenario.coletar()

    assert len(resumo.retidas) == quantos
    avisos = [
        r
        for r in caplog.records
        if r.getMessage() == "vistos: possível vandalismo em massa na fonte"
    ]
    assert len(avisos) == (1 if avisa else 0)
    if avisa:
        assert avisos[0].levelno == logging.WARNING
        assert getattr(avisos[0], "dados", None) == {
            "retidas": 23,
            "reconhecidos": 228,
            "percentual": 10.1,
        }


def test_o_registro_operacional_lista_os_retidos_com_a_categoria_exibida_e_a_lida(
    cenario: "Cenario", caplog: pytest.LogCaptureFixture
) -> None:
    primeira_coleta(cenario)
    cenario.editar("Algeria", rotulo="Visa not required")
    with caplog.at_level(logging.INFO, logger=LOG):
        cenario.coletar()
    [registro] = [r for r in caplog.records if r.getMessage() == "vistos: mudança retida"]
    assert registro.levelno == logging.WARNING
    assert getattr(registro, "dados", None) == {
        "codigo": "DZ",
        "exibida": "visto_exigido",
        "lida": "isento",
    }


# --------------------------------------------------------------------------- 12c
def test_mudanca_para_mais_exigente_e_aplicada_na_mesma_coleta(cenario: "Cenario") -> None:  # 12c
    primeira_coleta(cenario)
    cenario.editar("Albania", rotulo="Visa required")

    resumo = cenario.coletar()

    assert (resumo.aplicadas, resumo.retidas) == (1, ())
    albania = cenario.requisito("AL")
    assert albania is not None
    assert albania.categoria is EXIGIDO
    assert albania.lido_em == cenario.relogio.agora()
    assert albania.coleta_id == resumo.coleta_id
    assert cenario.mudancas() == []


def test_mudanca_para_outra_situacao_e_aplicada(cenario: "Cenario") -> None:
    primeira_coleta(cenario)
    cenario.editar("Albania", rotulo="Visa upon negotiation")
    resumo = cenario.coletar()
    albania = cenario.requisito("AL")
    assert albania is not None
    assert albania.categoria is OUTRA
    assert albania.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert albania.rotulo_original == "Visa upon negotiation"  # o rótulo fica à vista
    assert (resumo.aplicadas, resumo.retidas) == (1, ())


def test_mudanca_so_na_observacao_ou_na_permanencia_e_aplicada(cenario: "Cenario") -> None:
    primeira_coleta(cenario)
    cenario.editar("Albania", permanencia="60 days", notas="Nova observação.")
    resumo = cenario.coletar()
    albania = cenario.requisito("AL")
    assert albania is not None
    assert albania.categoria is ISENTO
    assert albania.permanencia_texto == "60 dias"
    assert [o["texto"] for o in albania.observacoes] == ["Nova observação."]
    assert (resumo.aplicadas, resumo.retidas) == (1, ())


# --------------------------------------------------------------------------- 12d
def test_outra_situacao_para_categoria_da_ordem_fica_retida(cenario: "Cenario") -> None:  # 12d
    primeira_coleta(cenario)
    antes = cenario.requisito("AS")
    assert antes is not None
    assert antes.categoria is OUTRA  # "Entry permit required" é um rótulo conhecido
    cenario.editar("American Samoa", rotulo="Visa required")

    resumo = cenario.coletar()

    [retida] = resumo.retidas
    assert (retida.codigo, retida.categoria_exibida, retida.categoria_lida) == (
        "AS",
        OUTRA,
        EXIGIDO,
    )
    depois = cenario.requisito("AS")
    assert depois is not None
    assert depois.categoria is OUTRA
    assert depois.lido_em == antes.lido_em


def test_sem_informacao_para_categoria_da_ordem_fica_retida(cenario: "Cenario") -> None:  # 12d
    linha_da_argelia = cenario.linha("Algeria")
    cenario.remover("Algeria")
    primeira_coleta(cenario)
    assert cenario.requisito("DZ") is None  # a fonte não trazia o país: "sem informação"

    cenario.acrescentar(linha_da_argelia)
    resumo = cenario.coletar()

    [retida] = resumo.retidas
    assert (retida.codigo, retida.categoria_exibida, retida.categoria_lida) == ("DZ", None, EXIGIDO)
    assert cenario.requisito("DZ") is None  # o painel continua como estava
    [mudanca] = cenario.mudancas("DZ")
    assert (mudanca.categoria_exibida, mudanca.categoria_lida) == (None, EXIGIDO)


def test_sem_informacao_para_outra_situacao_e_aplicada(cenario: "Cenario") -> None:
    linha_da_argelia = cenario.linha("Algeria")
    cenario.remover("Algeria")
    primeira_coleta(cenario)

    cenario.acrescentar(replace(linha_da_argelia, rotulo="Visa upon negotiation"))
    resumo = cenario.coletar()

    assert resumo.retidas == ()
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is OUTRA


# --------------------------------------------------------------------------- 12e
def test_primeira_coleta_valida_nao_retem_nada_mesmo_sem_dado_anterior(
    cenario: "Cenario",
) -> None:  # 12e
    resumo = cenario.coletar()
    assert resumo.retidas == ()
    assert cenario.mudancas() == []
    assert resumo.aplicadas == 228


# --------------------------------------------------------------------------- 12f
def test_retencao_some_sozinha_quando_a_fonte_volta_ao_valor_exibido(
    cenario: "Cenario",
) -> None:  # 12f
    primeira_coleta(cenario)
    original = cenario.linha("Algeria")
    cenario.editar("Algeria", rotulo="Visa not required")
    assert len(cenario.coletar().retidas) == 1
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo=original.rotulo)  # a fonte foi corrigida

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    assert (resumo.aplicadas, resumo.sem_mudanca) == (0, 228)
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is REVERTIDA
    assert mudanca.resolvida_em == cenario.relogio.agora()
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert argelia.lido_em == cenario.relogio.agora()  # a mesma fonte, confirmada hoje


# --------------------------------------------------------------------------- 12g
def dicionario_sem_o_rotulo(rotulo: str) -> Dicionario:
    base = dicionario_padrao()
    return replace(base, rotulos={k: v for k, v in base.rotulos.items() if k != rotulo})


def test_rotulo_que_o_dicionario_passa_a_reconhecer_e_aplicado_sem_retencao(
    cenario: "Cenario",
) -> None:  # 12g
    cenario.dicionario = dicionario_sem_o_rotulo("free visa on arrival")
    cenario.coletar()
    for codigo in ("LB", "MV", "PW"):
        pais = cenario.requisito(codigo)
        assert pais is not None
        assert pais.categoria is OUTRA
        assert pais.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
        assert pais.rotulo_original == "Free visa on arrival"  # à vista
    [item] = cenario.itens(TipoDeItemParaRevisao.ROTULO)
    assert (item.valor, item.estado) == ("free visa on arrival", EstadoDoItem.PENDENTE)
    cenario.semana_seguinte()

    cenario.dicionario = None  # o dono atualizou o dicionário; o texto da fonte não mudou
    resumo = cenario.coletar()

    assert (resumo.aplicadas, resumo.retidas) == (3, ())
    for codigo in ("LB", "MV", "PW"):
        pais = cenario.requisito(codigo)
        assert pais is not None
        assert pais.categoria is NA_CHEGADA
        assert pais.motivo_outra is None
    assert cenario.mudancas() == []
    [item] = cenario.itens(TipoDeItemParaRevisao.ROTULO)
    assert item.estado is EstadoDoItem.RESOLVIDO  # a coleta reconheceu o rótulo


def test_nome_que_o_dicionario_passa_a_reconhecer_e_aplicado_sem_retencao(
    cenario: "Cenario",
) -> None:
    base = dicionario_padrao()
    cenario.dicionario = replace(
        base, nomes={k: v for k, v in base.nomes.items() if k != "albania"}
    )
    primeira = cenario.coletar()
    assert primeira.nomes_nao_reconhecidos == ("Albania",)
    assert primeira.paises_reconhecidos == 227
    assert cenario.requisito("AL") is None  # sem informação, mas a linha está na fonte
    cenario.semana_seguinte()

    cenario.dicionario = None
    resumo = cenario.coletar()

    assert (resumo.aplicadas, resumo.retidas) == (1, ())
    albania = cenario.requisito("AL")
    assert albania is not None
    assert albania.categoria is ISENTO
    assert cenario.mudancas() == []
    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert item.estado is EstadoDoItem.RESOLVIDO


def test_nome_que_aparece_na_fonte_de_um_pais_sem_registro_depois_de_pronto_ainda_retem(
    cenario: "Cenario",
) -> None:
    # a linha é nova na fonte (não estava lá como nome pendente): vale a retenção
    cenario.remover("Albania")
    primeira_coleta(cenario)
    cenario.acrescentar(nome_novo("Albania"))
    resumo = cenario.coletar()
    assert [r.codigo for r in resumo.retidas] == ["AL"]
    assert cenario.requisito("AL") is None


# --------------------------------------------------------------------------- 12h
def test_passar_a_aceitar_so_o_rg_fica_retido(cenario: "Cenario") -> None:  # 12h
    primeira_coleta(cenario)
    venezuela = cenario.requisito("VE")
    assert venezuela is not None
    assert (venezuela.categoria, venezuela.aceita_rg) == (ISENTO, False)
    cenario.editar(
        "Venezuela",
        rotulo="Freedom of Movement",
        notas="Entry is allowed with a valid ID card that is less than 10 years old.",
    )

    resumo = cenario.coletar()

    [retida] = resumo.retidas
    assert (retida.codigo, retida.categoria_exibida, retida.categoria_lida) == (
        "VE",
        ISENTO,
        ISENTO,
    )
    assert (retida.aceita_rg_exibido, retida.aceita_rg_lido) == (False, True)
    depois = cenario.requisito("VE")
    assert depois is not None
    assert depois.aceita_rg is False  # o painel continua sem a indicação de RG
    [mudanca] = cenario.mudancas("VE")
    assert (mudanca.aceita_rg_exibido, mudanca.aceita_rg_lido) == (False, True)
    assert mudanca.candidato["aceita_rg"] is True


def test_deixar_de_aceitar_o_rg_e_aplicado(cenario: "Cenario") -> None:
    primeira_coleta(cenario)
    cenario.editar("Argentina", rotulo="Visa not required", notas="")
    resumo = cenario.coletar()
    assert resumo.retidas == ()
    argentina = cenario.requisito("AR")
    assert argentina is not None
    assert argentina.aceita_rg is False


# --------------------------------------------------------------------------- estados da retenção
def retida_de_argelia(cenario: "Cenario", rotulo: str = "Visa not required") -> None:
    primeira_coleta(cenario)
    cenario.editar("Algeria", rotulo=rotulo)
    assert [r.codigo for r in cenario.coletar().retidas] == ["DZ"]
    cenario.semana_seguinte()


def test_pendente_com_o_mesmo_valor_da_fonte_so_atualiza_a_coleta(cenario: "Cenario") -> None:
    retida_de_argelia(cenario)
    [antes] = cenario.mudancas("DZ")
    criada_em = antes.criada_em

    resumo = cenario.coletar()  # a fonte segue igual

    [depois] = cenario.mudancas("DZ")
    assert depois.id == antes.id
    assert depois.estado is PENDENTE
    assert depois.coleta_id == resumo.coleta_id
    assert depois.criada_em == criada_em
    assert [r.codigo for r in resumo.retidas] == ["DZ"]  # continua esperando o dono
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO


def test_rejeitada_nao_reabre_com_o_mesmo_valor_da_fonte(cenario: "Cenario") -> None:
    retida_de_argelia(cenario)
    [mudanca] = cenario.mudancas("DZ")
    MudancaRetidaRepositorio(cenario.sessao).rejeitar(mudanca, cenario.relogio.agora())
    cenario.semana_seguinte()

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    [depois] = cenario.mudancas("DZ")
    assert depois.id == mudanca.id
    assert depois.estado is REJEITADA
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert (resumo.aplicadas, resumo.sem_mudanca) == (0, 228)


def test_rejeitada_e_superada_quando_a_fonte_muda_para_outro_valor_e_a_decisao_recomeca(
    cenario: "Cenario",
) -> None:
    retida_de_argelia(cenario)
    [primeira] = cenario.mudancas("DZ")
    MudancaRetidaRepositorio(cenario.sessao).rejeitar(primeira, cenario.relogio.agora())
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa on arrival")  # outro valor, também menos exigente

    resumo = cenario.coletar()

    assert [(r.codigo, r.categoria_lida) for r in resumo.retidas] == [("DZ", NA_CHEGADA)]
    estados = [m.estado for m in cenario.mudancas("DZ")]
    assert estados == [SUPERADA, PENDENTE]


def test_pendente_e_superada_quando_a_fonte_muda_para_outro_valor_menos_exigente(
    cenario: "Cenario",
) -> None:
    retida_de_argelia(cenario)
    cenario.editar("Algeria", rotulo="Visa on arrival")

    resumo = cenario.coletar()

    assert [(r.codigo, r.categoria_lida) for r in resumo.retidas] == [("DZ", NA_CHEGADA)]
    primeira, segunda = cenario.mudancas("DZ")
    assert primeira.estado is SUPERADA
    assert primeira.resolvida_em == cenario.relogio.agora()
    assert segunda.estado is PENDENTE
    assert segunda.categoria_lida is NA_CHEGADA


def test_pendente_e_superada_quando_a_fonte_muda_para_valor_aplicavel(cenario: "Cenario") -> None:
    retida_de_argelia(cenario)
    # a fonte volta ao rótulo antigo, mas com nota nova: o hash é outro, e a mudança se aplica
    cenario.editar("Algeria", rotulo="Visa required", notas="Nota nova.")

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    assert resumo.aplicadas == 1
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is SUPERADA
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.observacoes[0]["texto"] == "Nota nova."


# --------------------------------------------------------------------------- linha que sai da fonte
def test_a_linha_sair_da_fonte_fica_retida_e_o_pais_mantem_o_ultimo_dado_valido(
    cenario: "Cenario",
) -> None:
    primeira = cenario.coletar()
    data_antiga = cenario.relogio.agora()
    cenario.semana_seguinte()
    cenario.remover("Algeria")

    resumo = cenario.coletar()

    assert resumo.valida
    assert resumo.paises_reconhecidos == 227
    assert (resumo.aplicadas, resumo.sem_mudanca) == (0, 227)
    [retida] = resumo.retidas
    assert (retida.codigo, retida.categoria_exibida, retida.categoria_lida) == ("DZ", EXIGIDO, None)
    argelia = cenario.requisito("DZ")  # o registro continua, com a data dele
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert argelia.lido_em == data_antiga
    assert argelia.coleta_id == primeira.coleta_id
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is PENDENTE
    assert (mudanca.categoria_exibida, mudanca.categoria_lida) == (EXIGIDO, None)
    assert mudanca.coleta_id == resumo.coleta_id


def test_a_linha_voltar_com_o_valor_exibido_reverte_a_saida_sem_confirmacao(
    cenario: "Cenario",
) -> None:
    primeira_coleta(cenario)
    linha = cenario.linha("Algeria")
    cenario.remover("Algeria")
    assert len(cenario.coletar().retidas) == 1
    cenario.semana_seguinte()
    cenario.acrescentar(linha)  # a edição maldosa foi desfeita

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    assert (resumo.aplicadas, resumo.sem_mudanca) == (0, 228)
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is REVERTIDA
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert argelia.lido_em == cenario.relogio.agora()


def test_vandalismo_que_apaga_linhas_e_e_desfeito_nunca_deixa_pais_sem_informacao(
    cenario: "Cenario",
) -> None:
    primeira_coleta(cenario)
    # 22 linhas a menos ainda passam nos 90% (206 de 228); mais que isso a coleta é rejeitada
    apagadas = [linha for linha in cenario.linhas if linha.tabela == TABELA_PRINCIPAL][:22]
    cenario.remover(*(linha.nome for linha in apagadas))

    apagou = cenario.coletar()

    assert apagou.valida
    assert len(apagou.retidas) == 22
    assert all(r.categoria_lida is None for r in apagou.retidas)
    assert len(cenario.requisitos()) == 228  # o site não mudou
    cenario.semana_seguinte()
    for linha in apagadas:
        cenario.acrescentar(linha)

    restaurou = cenario.coletar()

    assert restaurou.retidas == ()
    assert restaurou.sem_mudanca == 228
    assert {m.estado for m in cenario.mudancas()} == {REVERTIDA}
    assert len(cenario.requisitos()) == 228


def test_a_saida_retida_continua_uma_so_enquanto_a_linha_fica_fora(cenario: "Cenario") -> None:
    primeira_coleta(cenario)
    cenario.remover("Algeria")
    cenario.coletar()
    [antes] = cenario.mudancas("DZ")
    cenario.semana_seguinte()

    resumo = cenario.coletar()

    [depois] = cenario.mudancas("DZ")
    assert depois.id == antes.id
    assert depois.coleta_id == resumo.coleta_id
    assert [r.codigo for r in resumo.retidas] == ["DZ"]


def test_a_saida_rejeitada_nao_reabre_enquanto_a_linha_fica_fora(cenario: "Cenario") -> None:
    primeira_coleta(cenario)
    cenario.remover("Algeria")
    cenario.coletar()
    [mudanca] = cenario.mudancas("DZ")
    MudancaRetidaRepositorio(cenario.sessao).rejeitar(mudanca, cenario.relogio.agora())
    cenario.semana_seguinte()

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    assert [m.estado for m in cenario.mudancas("DZ")] == [REJEITADA]
    assert cenario.requisito("DZ") is not None


def test_a_retida_cuja_linha_some_da_fonte_e_superada_pela_saida(cenario: "Cenario") -> None:
    retida_de_argelia(cenario)
    cenario.remover("Algeria")

    resumo = cenario.coletar()

    assert [(r.codigo, r.categoria_lida) for r in resumo.retidas] == [("DZ", None)]
    assert [m.estado for m in cenario.mudancas("DZ")] == [SUPERADA, PENDENTE]
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO


def test_pais_sem_registro_com_retida_cuja_linha_sai_da_fonte_reverte(
    cenario: "Cenario",
) -> None:
    linha = cenario.linha("Algeria")
    cenario.remover("Algeria")
    primeira_coleta(cenario)
    cenario.acrescentar(linha)
    assert len(cenario.coletar().retidas) == 1
    cenario.semana_seguinte()
    cenario.remover("Algeria")  # volta ao que o site mostra: nada

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    assert [m.estado for m in cenario.mudancas("DZ")] == [REVERTIDA]
    assert cenario.requisito("DZ") is None


# --------------------------------------------------------------------------- só o dicionário mudou
def dicionario_com_a_categoria(rotulo: str, categoria: CategoriaDeVisto) -> Dicionario:
    base = dicionario_padrao()
    return replace(
        base, rotulos={**base.rotulos, rotulo: replace(base.rotulos[rotulo], categoria=categoria)}
    )


def test_mudanca_so_do_dicionario_entre_categorias_da_ordem_aplica_sem_reter_nas_duas_direcoes(
    cenario: "Cenario",
) -> None:
    # "evisa" é Autorização; o dono a passa para Visto exigido, depois a devolve, e ainda a passa
    # para Isento: mais exigente, menos exigente e de novo menos exigente, sempre com a fonte igual
    etapas = [
        (EXIGIDO, "mais exigente"),
        (CategoriaDeVisto.AUTORIZACAO_ELETRONICA, "menos exigente"),
        (ISENTO, "menos exigente"),
        (EXIGIDO, "mais exigente"),
    ]
    cenario.coletar()
    afegao = cenario.requisito("AF")  # "eVisa"
    assert afegao is not None
    assert afegao.categoria is CategoriaDeVisto.AUTORIZACAO_ELETRONICA
    hash_da_fonte = afegao.hash_fonte

    for categoria, _ in etapas:
        cenario.semana_seguinte()
        cenario.dicionario = dicionario_com_a_categoria("evisa", categoria)
        resumo = cenario.coletar()
        assert resumo.retidas == ()
        assert resumo.aplicadas >= 30  # todos os países com o rótulo "eVisa"
        assert afegao.categoria is categoria
        assert afegao.hash_fonte == hash_da_fonte  # a fonte não mudou
    assert cenario.mudancas() == []


# --------------------------------------------------------------------------- itens para revisão
def test_nome_desconhecido_vira_item_pendente_e_nao_afeta_nenhum_pais(
    cenario: "Cenario",
) -> None:
    cenario.acrescentar(nome_novo())
    resumo = cenario.coletar()

    assert resumo.valida
    assert resumo.nomes_nao_reconhecidos == ("Atlantis",)
    assert resumo.paises_reconhecidos == 228
    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert (item.valor, item.estado) == ("atlantis", EstadoDoItem.PENDENTE)
    assert item.primeira_vez_em == item.ultima_vez_em == cenario.relogio.agora()
    assert [(c["tabela"], c["nome_na_fonte"]) for c in item.contexto] == [("principal", "Atlantis")]
    assert len(cenario.requisitos()) == 228


def test_nome_pendente_e_resolvido_quando_uma_coleta_posterior_o_reconhece(
    cenario: "Cenario",
) -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.remover("Atlantis")  # a linha saiu da fonte

    cenario.coletar()

    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert item.estado is EstadoDoItem.RESOLVIDO
    assert item.resolvido_em == cenario.relogio.agora()


def test_nome_resolvido_que_reaparece_volta_a_pendente(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.remover("Atlantis")
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.acrescentar(nome_novo())

    cenario.coletar()

    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert item.estado is EstadoDoItem.PENDENTE
    assert item.resolvido_em is None


def test_nome_ignorado_nao_volta(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    ItemParaRevisaoRepositorio(cenario.sessao).ignorar_nome(
        item, "não existe no mapa", cenario.relogio.agora()
    )
    cenario.semana_seguinte()

    resumo = cenario.coletar()  # o nome continua na fonte

    [depois] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert depois.estado is EstadoDoItem.IGNORADO
    assert depois.motivo_ignorar == "não existe no mapa"
    assert resumo.nomes_nao_reconhecidos == ()  # já decidido pelo dono


def test_rotulo_desconhecido_deixa_o_pais_em_outra_situacao_com_o_rotulo_a_vista(
    cenario: "Cenario",
) -> None:
    cenario.editar("Albania", rotulo="Super visa")
    resumo = cenario.coletar()

    albania = cenario.requisito("AL")
    assert albania is not None
    assert albania.categoria is OUTRA
    assert albania.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert albania.rotulo_original == "Super visa"
    assert resumo.rotulos_nao_reconhecidos == ("super visa",)
    [item] = cenario.itens(TipoDeItemParaRevisao.ROTULO)
    assert (item.valor, item.estado) == ("super visa", EstadoDoItem.PENDENTE)
    assert [(c["tabela"], c["nome_na_fonte"]) for c in item.contexto] == [("principal", "Albania")]


def test_parte_desconhecida_de_um_combinado_leva_o_rotulo_inteiro_para_revisao(
    cenario: "Cenario",
) -> None:
    cenario.editar("Albania", rotulo="Visa not required / Super visa")
    cenario.coletar()
    [item] = cenario.itens(TipoDeItemParaRevisao.ROTULO)
    assert item.valor == "visa not required / super visa"


def test_rotulo_pendente_e_resolvido_quando_a_fonte_deixa_de_usa_lo(cenario: "Cenario") -> None:
    cenario.editar("Albania", rotulo="Super visa")
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Albania", rotulo="Visa not required")  # a fonte corrigiu o rótulo

    resumo = cenario.coletar()

    [item] = cenario.itens(TipoDeItemParaRevisao.ROTULO)
    assert item.estado is EstadoDoItem.RESOLVIDO
    # de "Outra situação" para uma categoria da ordem, com a fonte mudada: espera o dono (12d)
    assert [r.codigo for r in resumo.retidas] == ["AL"]


def hash_da_nota(nota: str) -> str:
    return hashlib.sha256(nota.encode("utf-8")).hexdigest()


def test_regra_por_pais_com_a_nota_alterada_abre_um_item_sem_invalidar_a_coleta(
    cenario: "Cenario",
) -> None:
    nota = "90 days (business), 6 months (tourist). Atualizado."
    cenario.editar("Jamaica", notas=nota)

    resumo = cenario.coletar()

    assert resumo.valida
    assert resumo.regras_para_reconfirmar == ("JM",)
    [item] = cenario.itens(TipoDeItemParaRevisao.REGRA)
    assert (item.valor, item.estado) == ("JM", EstadoDoItem.PENDENTE)
    assert item.contexto["hash_lido"] == hash_da_nota(nota)
    assert item.contexto["hash_esperado"] == dicionario_padrao().regras["JM"].hash_observacao
    assert item.contexto["texto"] == nota
    jamaica = cenario.requisito("JM")  # a regra continua valendo
    assert jamaica is not None
    assert jamaica.varia_conforme_motivo is True
    assert jamaica.permanencia_tipo == "varia_conforme_motivo"


def test_regra_por_pais_fecha_sozinha_quando_o_hash_volta_a_bater(cenario: "Cenario") -> None:
    original = cenario.linha("Jamaica").notas
    cenario.editar("Jamaica", notas="Outra nota.")
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Jamaica", notas=original)

    cenario.coletar()

    [item] = cenario.itens(TipoDeItemParaRevisao.REGRA)
    assert item.estado is EstadoDoItem.RESOLVIDO


def test_regra_por_pais_com_a_nota_da_fixture_nao_abre_item(cenario: "Cenario") -> None:
    cenario.coletar()
    assert cenario.itens(TipoDeItemParaRevisao.REGRA) == []
