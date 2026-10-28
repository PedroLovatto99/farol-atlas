"""Serviço do dono: listar pendências, confirmar, rejeitar e ignorar nome (FR-010a, FR-012b)."""

from typing import TYPE_CHECKING

import pytest

from farol.dominio import (
    CategoriaDeVisto,
    EstadoDaRetencao,
    EstadoDoItem,
    TipoDeItemParaRevisao,
)
from farol.vistos import ErroDoDono, ServicoDoDono, dicionario_padrao
from farol.vistos.fonte import TABELA_PRINCIPAL, LinhaDaFonte

if TYPE_CHECKING:
    from tests.integracao.vistos.conftest import Cenario

ISENTO = CategoriaDeVisto.ISENTO
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO


def dono(cenario: "Cenario") -> ServicoDoDono:
    return ServicoDoDono(cenario.sessao, cenario.relogio)


def semana_com_a_argelia_retida(cenario: "Cenario") -> None:
    """Primeira coleta, e uma segunda em que a Argélia passa a 'Visa not required' (retida)."""
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required", permanencia="90 days")
    assert len(cenario.coletar().retidas) == 1
    cenario.semana_seguinte()


def nome_novo(nome: str = "Atlantis") -> LinhaDaFonte:
    return LinhaDaFonte(TABELA_PRINCIPAL, None, nome, "Visa not required", "", "")


# --------------------------------------------------------------------------- listar
def test_sem_pendencias_a_lista_vem_vazia(cenario: "Cenario") -> None:
    cenario.coletar()
    pendencias = dono(cenario).listar_pendentes()
    assert pendencias.total == 0
    assert (pendencias.retidas, pendencias.nomes, pendencias.rotulos, pendencias.regras) == (
        (),
        (),
        (),
        (),
    )


def test_a_lista_mostra_a_retida_com_a_categoria_exibida_a_lida_e_a_data_do_dado_exibido(
    cenario: "Cenario",
) -> None:
    primeira = cenario.relogio.agora()
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required")
    cenario.coletar()
    retida_em = cenario.relogio.agora()
    cenario.semana_seguinte()

    [retida] = dono(cenario).listar_pendentes().retidas

    assert retida.codigo == "DZ"
    assert (retida.categoria_exibida, retida.categoria_lida) == (EXIGIDO, ISENTO)
    assert (retida.aceita_rg_exibido, retida.aceita_rg_lido) == (False, False)
    assert retida.desde == retida_em
    assert retida.dado_exibido_de == primeira  # a data do dado que o painel ainda mostra


def test_a_retida_de_pais_sem_registro_mostra_sem_informacao_e_sem_data(
    cenario: "Cenario",
) -> None:
    linha = cenario.linha("Algeria")
    cenario.remover("Algeria")
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.acrescentar(linha)
    cenario.coletar()

    [retida] = dono(cenario).listar_pendentes().retidas

    assert (retida.categoria_exibida, retida.categoria_lida) == (None, EXIGIDO)
    assert retida.dado_exibido_de is None


def test_a_lista_traz_nomes_rotulos_e_regras_com_o_hash_novo(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.editar("Albania", rotulo="Super visa")
    cenario.editar("Jamaica", notas="Outra nota.")
    cenario.coletar()

    pendencias = dono(cenario).listar_pendentes()

    assert [n.valor for n in pendencias.nomes] == ["atlantis"]
    assert pendencias.nomes[0].contexto[0]["nome_na_fonte"] == "Atlantis"
    assert [r.valor for r in pendencias.rotulos] == ["super visa"]
    assert pendencias.rotulos[0].contexto[0]["nome_na_fonte"] == "Albania"
    [regra] = pendencias.regras
    assert regra.codigo == "JM"
    assert regra.hash_esperado == dicionario_padrao().regras["JM"].hash_observacao
    assert len(regra.hash_lido) == 64
    assert regra.hash_lido != regra.hash_esperado
    assert regra.texto == "Outra nota."
    assert pendencias.total == 3


def test_so_entra_na_lista_o_que_esta_pendente(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.remover("Atlantis")
    cenario.coletar()  # o nome foi resolvido sozinho
    assert dono(cenario).listar_pendentes().nomes == ()


# --------------------------------------------------------------------------- confirmar
def test_confirmar_aplica_o_candidato_com_a_data_da_coleta_que_o_leu(cenario: "Cenario") -> None:
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required", permanencia="90 days", notas="Nota nova.")
    resumo = cenario.coletar()
    lida_em = cenario.relogio.agora()
    cenario.semana_seguinte()
    cenario.semana_seguinte()  # o dono confirma duas semanas depois

    confirmada = dono(cenario).confirmar("DZ")

    assert (confirmada.codigo, confirmada.categoria_lida) == ("DZ", ISENTO)
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is ISENTO
    assert argelia.rotulo_original == "Visa not required"
    assert argelia.permanencia_tipo == "padronizada"
    assert argelia.permanencia_texto == "90 dias"
    assert argelia.lido_em == lida_em  # a data da coleta que leu, não a da confirmação
    assert argelia.coleta_id == resumo.coleta_id
    assert argelia.observacoes[0]["texto"] == "Nota nova."
    assert argelia.observacoes[0]["traducao"] == "[pt] Nota nova."
    assert len(argelia.hash_fonte) == 64
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is EstadoDaRetencao.CONFIRMADA
    assert mudanca.resolvida_em == cenario.relogio.agora()


def test_confirmar_pais_sem_registro_cria_o_registro(cenario: "Cenario") -> None:
    linha = cenario.linha("Algeria")
    cenario.remover("Algeria")
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.acrescentar(linha)
    cenario.coletar()
    assert cenario.requisito("DZ") is None

    dono(cenario).confirmar("DZ")

    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO


def test_confirmar_aceita_o_codigo_em_minusculas(cenario: "Cenario") -> None:
    semana_com_a_argelia_retida(cenario)
    assert dono(cenario).confirmar(" dz ").codigo == "DZ"


def test_depois_de_confirmar_a_coleta_seguinte_nao_retem_de_novo(cenario: "Cenario") -> None:
    semana_com_a_argelia_retida(cenario)
    dono(cenario).confirmar("DZ")

    resumo = cenario.coletar()

    assert resumo.retidas == ()
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is ISENTO
    assert argelia.lido_em == cenario.relogio.agora()
    assert [m.estado for m in cenario.mudancas("DZ")] == [EstadoDaRetencao.CONFIRMADA]


def test_confirmar_o_rg_liga_a_indicacao_no_registro(cenario: "Cenario") -> None:
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar(
        "Venezuela",
        rotulo="Freedom of Movement",
        notas="Entry is allowed with a valid ID card that is less than 10 years old.",
    )
    cenario.coletar()
    venezuela = cenario.requisito("VE")
    assert venezuela is not None
    assert venezuela.aceita_rg is False

    dono(cenario).confirmar("VE")

    assert venezuela.aceita_rg is True


def test_confirmar_todos_aplica_todas_as_retidas(cenario: "Cenario") -> None:
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa not required")
    cenario.editar("Bangladesh", rotulo="Visa on arrival")
    cenario.editar("Brunei", rotulo="eVisa")
    assert len(cenario.coletar().retidas) == 3

    codigos = dono(cenario).confirmar_todos()

    assert codigos == ("BD", "BN", "DZ")
    assert cenario.requisito("DZ").categoria is ISENTO  # type: ignore[union-attr]
    assert cenario.requisito("BD").categoria is CategoriaDeVisto.VISTO_NA_CHEGADA  # type: ignore[union-attr]
    assert cenario.requisito("BN").categoria is CategoriaDeVisto.AUTORIZACAO_ELETRONICA  # type: ignore[union-attr]
    assert dono(cenario).listar_pendentes().retidas == ()
    assert {m.estado for m in cenario.mudancas()} == {EstadoDaRetencao.CONFIRMADA}


def test_confirmar_todos_sem_retidas_nao_faz_nada(cenario: "Cenario") -> None:
    cenario.coletar()
    assert dono(cenario).confirmar_todos() == ()


def test_confirmar_codigo_sem_mudanca_retida_da_erro(cenario: "Cenario") -> None:
    cenario.coletar()
    with pytest.raises(ErroDoDono, match="AR"):
        dono(cenario).confirmar("AR")


def test_confirmar_o_que_ja_foi_rejeitado_da_erro(cenario: "Cenario") -> None:
    semana_com_a_argelia_retida(cenario)
    servico = dono(cenario)
    servico.rejeitar("DZ")
    with pytest.raises(ErroDoDono, match="DZ"):
        servico.confirmar("DZ")


def test_confirmar_a_saida_da_linha_volta_o_pais_para_sem_informacao(cenario: "Cenario") -> None:
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.remover("Algeria")
    cenario.coletar()
    cenario.semana_seguinte()
    [retida] = dono(cenario).listar_pendentes().retidas
    assert (retida.categoria_exibida, retida.categoria_lida) == (EXIGIDO, None)

    confirmada = dono(cenario).confirmar("DZ")

    assert confirmada.categoria_lida is None
    assert cenario.requisito("DZ") is None  # agora sim: "Sem informação de visto"
    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is EstadoDaRetencao.CONFIRMADA
    assert cenario.coletar().retidas == ()  # a linha segue fora: nada novo
    assert cenario.requisito("DZ") is None


def test_confirmar_todos_inclui_as_saidas_de_linha(cenario: "Cenario") -> None:
    cenario.coletar()
    cenario.semana_seguinte()
    cenario.remover("Algeria")
    cenario.editar("Bangladesh", rotulo="Visa on arrival")
    cenario.coletar()

    assert dono(cenario).confirmar_todos() == ("BD", "DZ")
    assert cenario.requisito("DZ") is None
    assert cenario.requisito("BD") is not None


# --------------------------------------------------------------------------- rejeitar
def test_rejeitar_mantem_o_dado_antigo_e_marca_a_mudanca_como_rejeitada(
    cenario: "Cenario",
) -> None:
    semana_com_a_argelia_retida(cenario)

    dono(cenario).rejeitar("DZ")

    [mudanca] = cenario.mudancas("DZ")
    assert mudanca.estado is EstadoDaRetencao.REJEITADA
    assert mudanca.resolvida_em == cenario.relogio.agora()
    argelia = cenario.requisito("DZ")
    assert argelia is not None
    assert argelia.categoria is EXIGIDO
    assert dono(cenario).listar_pendentes().retidas == ()


def test_rejeitar_vale_enquanto_a_fonte_mantem_o_valor_e_recomeca_se_ela_mudar(
    cenario: "Cenario",
) -> None:
    semana_com_a_argelia_retida(cenario)
    dono(cenario).rejeitar("DZ")

    assert cenario.coletar().retidas == ()  # o mesmo valor: não reabre
    cenario.semana_seguinte()
    cenario.editar("Algeria", rotulo="Visa on arrival")
    resumo = cenario.coletar()  # outro valor: o dono é consultado de novo
    assert [r.codigo for r in resumo.retidas] == ["DZ"]


def test_rejeitar_codigo_sem_mudanca_retida_da_erro(cenario: "Cenario") -> None:
    cenario.coletar()
    with pytest.raises(ErroDoDono, match="AR"):
        dono(cenario).rejeitar("AR")


# --------------------------------------------------------------------------- ignorar nome
def test_ignorar_nome_pendente_grava_o_motivo(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()

    dono(cenario).ignorar_nome("atlantis", "não existe no mapa")  # sem diferenciar a caixa

    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert item.estado is EstadoDoItem.IGNORADO
    assert item.motivo_ignorar == "não existe no mapa"
    assert item.resolvido_em == cenario.relogio.agora()
    assert dono(cenario).listar_pendentes().nomes == ()


@pytest.mark.parametrize("motivo", ["", "   "])
def test_ignorar_nome_exige_motivo(cenario: "Cenario", motivo: str) -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    with pytest.raises(ErroDoDono, match="motivo"):
        dono(cenario).ignorar_nome("Atlantis", motivo)
    [item] = cenario.itens(TipoDeItemParaRevisao.NOME)
    assert item.estado is EstadoDoItem.PENDENTE


def test_ignorar_nome_que_nao_esta_pendente_da_erro(cenario: "Cenario") -> None:
    cenario.coletar()
    with pytest.raises(ErroDoDono, match="Atlantis"):
        dono(cenario).ignorar_nome("Atlantis", "motivo")


def test_ignorar_nome_ja_ignorado_da_erro(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo())
    cenario.coletar()
    servico = dono(cenario)
    servico.ignorar_nome("Atlantis", "motivo")
    with pytest.raises(ErroDoDono):
        servico.ignorar_nome("Atlantis", "motivo")


def test_rotulo_e_regra_nao_podem_ser_ignorados(cenario: "Cenario") -> None:
    cenario.editar("Albania", rotulo="Super visa")
    cenario.editar("Jamaica", notas="Outra nota.")
    cenario.coletar()
    servico = dono(cenario)
    with pytest.raises(ErroDoDono):
        servico.ignorar_nome("Super visa", "motivo")
    with pytest.raises(ErroDoDono):
        servico.ignorar_nome("JM", "motivo")
    estados = {i.tipo: i.estado for i in cenario.itens()}
    assert estados[TipoDeItemParaRevisao.ROTULO] is EstadoDoItem.PENDENTE
    assert estados[TipoDeItemParaRevisao.REGRA] is EstadoDoItem.PENDENTE


def test_outras_pendencias_nao_somem_ao_ignorar_um_nome(cenario: "Cenario") -> None:
    cenario.acrescentar(nome_novo("Atlantis"))
    cenario.acrescentar(nome_novo("Lemuria"))
    cenario.coletar()
    dono(cenario).ignorar_nome("Atlantis", "motivo")
    assert [n.valor for n in dono(cenario).listar_pendentes().nomes] == ["lemuria"]
