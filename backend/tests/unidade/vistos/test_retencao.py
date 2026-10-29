"""Retenção por país (FR-010a): a tabela de transições de `decidir_retencao`, em testes."""

import itertools

import pytest

from farol.dominio import CategoriaDeVisto as Cat
from farol.dominio import EstadoDaRetencao as Estado
from farol.dominio import MotivoOutraSituacao
from farol.vistos.retencao import (
    HASH_SEM_LINHA,
    Aberta,
    AcaoDaRetencao,
    DecisaoDeRetencao,
    Situacao,
    decidir_retencao,
)

ISENTO, NA_CHEGADA, ELETRONICA, EXIGIDO, OUTRA = (
    Cat.ISENTO,
    Cat.VISTO_NA_CHEGADA,
    Cat.AUTORIZACAO_ELETRONICA,
    Cat.VISTO_EXIGIDO,
    Cat.OUTRA_SITUACAO,
)
ORDEM = (ISENTO, NA_CHEGADA, ELETRONICA, EXIGIDO)

H1, H2, H3 = "1" * 64, "2" * 64, "3" * 64

SEM_MUDANCA = AcaoDaRetencao.SEM_MUDANCA
APLICAR = AcaoDaRetencao.APLICAR
RETER = AcaoDaRetencao.RETER
ATUALIZAR = AcaoDaRetencao.ATUALIZAR_RETIDA
MANTER_REJEITADA = AcaoDaRetencao.MANTER_REJEITADA


def situacao(
    categoria: Cat,
    hash_fonte: str = H1,
    *,
    rg: bool = False,
    motivo_outra: MotivoOutraSituacao | None = None,
    permanencia_tipo: str = "nenhuma",
    permanencia_texto: str | None = None,
) -> Situacao:
    """Uma situação de visto; `OUTRA` leva o motivo que o banco exige."""
    if categoria is OUTRA and motivo_outra is None:
        motivo_outra = MotivoOutraSituacao.ROTULO_CONHECIDO
    return Situacao(
        categoria,
        hash_fonte,
        aceita_rg=rg,
        motivo_outra=motivo_outra,
        permanencia_tipo=permanencia_tipo,
        permanencia_texto=permanencia_texto,
    )


# --------------------------------------------------------------------------- categoria da ordem
@pytest.mark.parametrize(
    ("exibido", "lido"), list(itertools.product(ORDEM, ORDEM)), ids=lambda c: c.value
)
def test_dentro_da_ordem_so_a_mudanca_para_menos_exigente_retem(exibido: Cat, lido: Cat) -> None:
    # a fonte mudou (hash diferente)
    decisao = decidir_retencao(situacao(exibido, H1), situacao(lido, H2))
    menos_exigente = ORDEM.index(lido) < ORDEM.index(exibido)
    assert decisao.acao is (RETER if menos_exigente else APLICAR)
    assert decisao.encerrar is None


def test_isento_para_visto_exigido_aplica_na_mesma_coleta() -> None:  # 12c
    assert decidir_retencao(situacao(ISENTO), situacao(EXIGIDO, H2)).acao is APLICAR


def test_visto_exigido_para_isento_retem() -> None:  # 12a e 12b: vale com um país só
    assert decidir_retencao(situacao(EXIGIDO), situacao(ISENTO, H2)).acao is RETER


# --------------------------------------------------------------------------- "Outra situação"
@pytest.mark.parametrize("lido", ORDEM, ids=lambda c: c.value)
def test_outra_situacao_para_qualquer_categoria_da_ordem_retem(lido: Cat) -> None:  # 12d
    assert decidir_retencao(situacao(OUTRA), situacao(lido, H2)).acao is RETER


@pytest.mark.parametrize("exibido", ORDEM, ids=lambda c: c.value)
def test_qualquer_categoria_da_ordem_para_outra_situacao_aplica(exibido: Cat) -> None:
    assert decidir_retencao(situacao(exibido), situacao(OUTRA, H2)).acao is APLICAR


def test_outra_situacao_para_outra_situacao_com_a_fonte_mudada_aplica() -> None:
    assert decidir_retencao(situacao(OUTRA), situacao(OUTRA, H2)).acao is APLICAR


# --------------------------------------------------------------------------- "sem informação"
@pytest.mark.parametrize("lido", ORDEM, ids=lambda c: c.value)
def test_sem_informacao_para_qualquer_categoria_da_ordem_retem(lido: Cat) -> None:  # 12d
    # o país não tinha registro, e a linha dele apareceu na fonte
    assert decidir_retencao(None, situacao(lido)).acao is RETER


def test_sem_informacao_para_outra_situacao_aplica() -> None:
    assert decidir_retencao(None, situacao(OUTRA)).acao is APLICAR


@pytest.mark.parametrize("exibido", [*ORDEM, OUTRA], ids=lambda c: c.value)
def test_a_linha_sair_da_fonte_retem_a_volta_para_sem_informacao(exibido: Cat) -> None:
    # o país continua com o último dado válido até o dono confirmar
    decisao = decidir_retencao(situacao(exibido), None)
    assert decisao == DecisaoDeRetencao(RETER)


def test_sem_registro_e_sem_linha_na_fonte_nao_muda_nada() -> None:
    assert decidir_retencao(None, None).acao is SEM_MUDANCA


# --------------------------------------------------------------------------- RG
def test_passar_a_aceitar_so_o_rg_retem_mesmo_na_mesma_categoria() -> None:  # 12h
    decisao = decidir_retencao(situacao(ISENTO, H1, rg=False), situacao(ISENTO, H2, rg=True))
    assert decisao.acao is RETER


def test_deixar_de_aceitar_o_rg_aplica() -> None:
    decisao = decidir_retencao(situacao(ISENTO, H1, rg=True), situacao(ISENTO, H2, rg=False))
    assert decisao.acao is APLICAR


def test_continuar_aceitando_o_rg_com_outra_mudanca_aplica() -> None:
    decisao = decidir_retencao(
        situacao(ISENTO, H1, rg=True, permanencia_texto="90 dias", permanencia_tipo="padronizada"),
        situacao(ISENTO, H2, rg=True, permanencia_texto="30 dias", permanencia_tipo="padronizada"),
    )
    assert decisao.acao is APLICAR


def test_do_visto_exigido_para_isento_com_rg_retem() -> None:
    assert decidir_retencao(situacao(EXIGIDO), situacao(ISENTO, H2, rg=True)).acao is RETER


def test_pais_sem_registro_que_aparece_com_rg_retem() -> None:
    assert decidir_retencao(None, situacao(ISENTO, rg=True)).acao is RETER


# ------------------------------------------------------------------ mudança só do dicionário
def test_fonte_igual_e_derivados_diferentes_e_mudanca_do_dicionario_e_aplica() -> None:  # 12g
    exibido = situacao(OUTRA, H1, motivo_outra=MotivoOutraSituacao.ROTULO_DESCONHECIDO)
    lido = situacao(ISENTO, H1)
    decisao = decidir_retencao(exibido, lido)
    assert decisao.acao is APLICAR
    assert decisao.encerrar is None


@pytest.mark.parametrize("lido", ORDEM, ids=lambda c: c.value)
def test_dicionario_que_passa_a_reconhecer_o_rotulo_nunca_retem(lido: Cat) -> None:
    assert decidir_retencao(situacao(OUTRA, H1), situacao(lido, H1)).acao is APLICAR


@pytest.mark.parametrize(
    ("exibido", "lido"),
    [par for par in itertools.product(ORDEM, ORDEM) if par[0] is not par[1]],
    ids=lambda c: c.value,
)
def test_mudanca_so_do_dicionario_entre_categorias_da_ordem_aplica_nas_duas_direcoes(
    exibido: Cat, lido: Cat
) -> None:
    # a fonte é a mesma (mesmo hash): vale tanto para mais quanto para menos exigente
    decisao = decidir_retencao(situacao(exibido, H1), situacao(lido, H1))
    assert decisao == DecisaoDeRetencao(APLICAR)


@pytest.mark.parametrize("categoria", ORDEM, ids=lambda c: c.value)
def test_mudanca_so_do_dicionario_de_e_para_outra_situacao_aplica(categoria: Cat) -> None:
    assert decidir_retencao(situacao(OUTRA, H1), situacao(categoria, H1)).acao is APLICAR
    assert decidir_retencao(situacao(categoria, H1), situacao(OUTRA, H1)).acao is APLICAR


def test_dicionario_que_passa_a_aceitar_o_rg_com_a_fonte_igual_aplica() -> None:
    decisao = decidir_retencao(situacao(ISENTO, H1, rg=False), situacao(ISENTO, H1, rg=True))
    assert decisao.acao is APLICAR


def test_fonte_e_derivados_iguais_so_renovam_a_data() -> None:
    assert decidir_retencao(situacao(ISENTO, H1), situacao(ISENTO, H1)).acao is SEM_MUDANCA


def test_mudanca_so_na_permanencia_derivada_do_dicionario_aplica() -> None:
    exibido = situacao(ISENTO, H1, permanencia_tipo="original", permanencia_texto="3 months")
    lido = situacao(ISENTO, H1, permanencia_tipo="padronizada", permanencia_texto="3 meses")
    assert decidir_retencao(exibido, lido).acao is APLICAR


def test_nome_pendente_que_passa_a_ser_reconhecido_aplica_sem_retencao() -> None:
    # o país não tinha registro; a linha já estava na fonte e só o dicionário mudou
    assert decidir_retencao(None, situacao(ISENTO), fonte_ja_lida=True).acao is APLICAR


def test_fonte_ja_lida_nao_afrouxa_a_retencao_de_quem_tem_registro() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(ISENTO, H2), fonte_ja_lida=True)
    assert decisao.acao is RETER


# --------------------------------------------------------------------------- primeira coleta
@pytest.mark.parametrize(
    "lido", [situacao(c) for c in (*ORDEM, OUTRA)] + [situacao(ISENTO, rg=True)]
)
def test_primeira_coleta_valida_aplica_tudo(lido: Situacao) -> None:  # 12e
    assert decidir_retencao(None, lido, primeira_coleta=True).acao is APLICAR


def test_primeira_coleta_sem_linha_na_fonte_nao_muda_nada() -> None:
    assert decidir_retencao(None, None, primeira_coleta=True).acao is SEM_MUDANCA


# --------------------------------------------------------------------------- retenção pendente
def pendente(hash_lido: str) -> Aberta:
    return Aberta(Estado.PENDENTE, hash_lido)


def rejeitada(hash_lido: str) -> Aberta:
    return Aberta(Estado.REJEITADA, hash_lido)


def test_pendente_com_o_mesmo_hash_lido_so_atualiza_a_coleta() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(ISENTO, H2), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(ATUALIZAR)


def test_pendente_quando_a_fonte_volta_ao_valor_exibido_e_revertida() -> None:  # 12f
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(EXIGIDO, H1), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(SEM_MUDANCA, Estado.REVERTIDA)


def test_a_fonte_voltar_ao_valor_exibido_reverte_ate_com_a_categoria_do_dicionario_nova() -> None:
    # voltou ao hash exibido, mas o dicionário também mudou: reverte e aplica o derivado
    decisao = decidir_retencao(situacao(OUTRA, H1), situacao(ISENTO, H1), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(APLICAR, Estado.REVERTIDA)


def test_pendente_quando_a_fonte_mudou_para_outro_valor_menos_exigente_e_superada() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(NA_CHEGADA, H3), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(RETER, Estado.SUPERADA)


def test_pendente_quando_a_fonte_mudou_para_valor_mais_exigente_e_superada_e_aplica() -> None:
    decisao = decidir_retencao(situacao(ISENTO, H1), situacao(EXIGIDO, H3), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(APLICAR, Estado.SUPERADA)


def test_pendente_de_outro_valor_quando_a_linha_sai_da_fonte_e_superada_e_retem_a_saida() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), None, aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(RETER, Estado.SUPERADA)


# --------------------------------------------------------------------------- linha que sai da fonte
def test_a_saida_retida_so_atualiza_a_coleta_enquanto_a_linha_continua_fora() -> None:
    decisao = decidir_retencao(
        situacao(EXIGIDO, H1), None, aberta=Aberta(Estado.PENDENTE, HASH_SEM_LINHA)
    )
    assert decisao == DecisaoDeRetencao(ATUALIZAR)


def test_a_saida_rejeitada_nao_retem_de_novo_enquanto_a_linha_continua_fora() -> None:
    decisao = decidir_retencao(
        situacao(EXIGIDO, H1), None, aberta=Aberta(Estado.REJEITADA, HASH_SEM_LINHA)
    )
    assert decisao == DecisaoDeRetencao(MANTER_REJEITADA)


def test_a_linha_voltar_com_o_valor_exibido_reverte_a_saida_retida() -> None:
    # vandalismo que apaga a linha e é desfeito: nada a confirmar, o país nunca saiu do ar
    decisao = decidir_retencao(
        situacao(EXIGIDO, H1), situacao(EXIGIDO, H1), aberta=Aberta(Estado.PENDENTE, HASH_SEM_LINHA)
    )
    assert decisao == DecisaoDeRetencao(SEM_MUDANCA, Estado.REVERTIDA)


def test_a_linha_voltar_com_outro_valor_supera_a_saida_retida() -> None:
    decisao = decidir_retencao(
        situacao(EXIGIDO, H1), situacao(ISENTO, H3), aberta=Aberta(Estado.PENDENTE, HASH_SEM_LINHA)
    )
    assert decisao == DecisaoDeRetencao(RETER, Estado.SUPERADA)  # menos exigente: retém de novo


def test_a_linha_voltar_mais_exigente_supera_a_saida_retida_e_aplica() -> None:
    decisao = decidir_retencao(
        situacao(ISENTO, H1), situacao(EXIGIDO, H3), aberta=Aberta(Estado.PENDENTE, HASH_SEM_LINHA)
    )
    assert decisao == DecisaoDeRetencao(APLICAR, Estado.SUPERADA)


def test_uma_retencao_comum_e_superada_quando_a_linha_sai() -> None:
    # o hash lido da retenção aberta não é o da saída: a decisão recomeça
    assert HASH_SEM_LINHA not in (H1, H2, H3)
    decisao = decidir_retencao(situacao(EXIGIDO, H1), None, aberta=rejeitada(H2))
    assert decisao == DecisaoDeRetencao(RETER, Estado.SUPERADA)


def test_pendente_de_pais_sem_registro_reverte_quando_a_linha_sai_da_fonte() -> None:
    decisao = decidir_retencao(None, None, aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(SEM_MUDANCA, Estado.REVERTIDA)


def test_pendente_de_pais_sem_registro_com_o_mesmo_hash_so_atualiza() -> None:
    assert decidir_retencao(None, situacao(ISENTO, H2), aberta=pendente(H2)).acao is ATUALIZAR


def test_pendente_cuja_decisao_deixou_de_ser_reter_e_superada() -> None:
    # o mesmo hash lido, mas o dicionário passou a tratá-lo como mais exigente
    decisao = decidir_retencao(situacao(ISENTO, H1), situacao(EXIGIDO, H2), aberta=pendente(H2))
    assert decisao == DecisaoDeRetencao(APLICAR, Estado.SUPERADA)


# --------------------------------------------------------------------------- retenção rejeitada
def test_rejeitada_com_o_mesmo_hash_lido_nao_retem_de_novo() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(ISENTO, H2), aberta=rejeitada(H2))
    assert decisao == DecisaoDeRetencao(MANTER_REJEITADA)


def test_rejeitada_quando_a_fonte_volta_ao_valor_exibido_e_revertida() -> None:
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(EXIGIDO, H1), aberta=rejeitada(H2))
    assert decisao == DecisaoDeRetencao(SEM_MUDANCA, Estado.REVERTIDA)


def test_rejeitada_quando_a_fonte_mudou_para_outro_valor_recomeca_a_decisao() -> None:
    # outro valor menos exigente: a decisão recomeça, e o dono é consultado de novo
    decisao = decidir_retencao(situacao(EXIGIDO, H1), situacao(ISENTO, H3), aberta=rejeitada(H2))
    assert decisao == DecisaoDeRetencao(RETER, Estado.SUPERADA)


def test_rejeitada_quando_a_fonte_mudou_para_valor_mais_exigente_aplica() -> None:
    decisao = decidir_retencao(situacao(ISENTO, H1), situacao(EXIGIDO, H3), aberta=rejeitada(H2))
    assert decisao == DecisaoDeRetencao(APLICAR, Estado.SUPERADA)


def test_rejeitada_de_pais_sem_registro_com_o_mesmo_hash_nao_retem_de_novo() -> None:
    assert (
        decidir_retencao(None, situacao(ISENTO, H2), aberta=rejeitada(H2)).acao is MANTER_REJEITADA
    )


# --------------------------------------------------------------------------- disciplina da função
def test_a_decisao_nao_olha_para_a_retencao_aberta_na_primeira_coleta() -> None:
    # sem dado anterior não existe retenção: aplicar vence
    assert (
        decidir_retencao(None, situacao(ISENTO), primeira_coleta=True, aberta=pendente(H2)).acao
        is APLICAR
    )


def test_decidir_retencao_e_pura() -> None:
    exibido, lido = situacao(EXIGIDO, H1), situacao(ISENTO, H2)
    assert decidir_retencao(exibido, lido) == decidir_retencao(exibido, lido)
