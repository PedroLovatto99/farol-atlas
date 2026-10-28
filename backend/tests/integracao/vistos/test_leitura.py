"""Leitura dos vistos para a API: as cinco regras de "Como a leitura resolve o visto de um
território" (data-model.md), a data de cada dado e o número fixo de consultas.

Os dados vêm da coleta de verdade sobre a página real, no seed completo do mapa.
"""

from typing import TYPE_CHECKING

import pytest

from farol.dominio import Territorio, TipoTerritorio
from farol.vistos import (
    LICENCA_DA_FONTE,
    NOME_DA_FONTE,
    URL_DO_ARTIGO,
    OrigemDoVisto,
    SituacaoDeVisto,
    SituacaoNoGlobo,
    TipoDePermanencia,
    VisaoDoVisto,
    montar_visto_do_pais,
    montar_vistos_do_mapa,
)

if TYPE_CHECKING:
    from tests.conftest import ContadorDeConsultas
    from tests.integracao.vistos.conftest import Cenario

    from farol.vistos import VisaoDosVistos

# Territórios com painel no seed (todos menos as áreas neutras), contando o Brasil
TERRITORIOS_COM_PAINEL = 238
# Dependências comuns que a fonte não traz em linha própria: usam o soberano (regra 4)
SEM_LINHA_PROPRIA = ("GG", "JE", "IM", "AX", "NF", "UM", "IOA", "ATC", "CSI")


def visto_de(cenario: "Cenario", codigo: str) -> VisaoDoVisto:
    visto = montar_visto_do_pais(cenario.sessao, codigo, cenario.relogio)
    assert visto is not None, f"{codigo} devia ter a seção de visto"
    return visto


def mapa_de(cenario: "Cenario") -> "VisaoDosVistos":
    return montar_vistos_do_mapa(cenario.sessao, cenario.relogio)


def por_codigo(mapa: "VisaoDosVistos") -> dict[str, tuple[SituacaoNoGlobo, bool]]:
    return {t.codigo: (t.situacao, t.aceita_rg) for t in mapa.territorios}


# --------------------------------------------------------------------------- regra 1
def test_o_brasil_nao_tem_secao_de_visto_e_no_globo_nao_se_aplica(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()

    assert montar_visto_do_pais(cenario_completo.sessao, "BR", cenario_completo.relogio) is None
    assert por_codigo(mapa_de(cenario_completo))["BR"] == (SituacaoNoGlobo.NAO_SE_APLICA, False)


def test_area_neutra_e_codigo_desconhecido_ficam_sem_visto_e_fora_do_globo(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.sessao.add(
        Territorio(codigo="EH", nome_pt="Saara Ocidental", tipo=TipoTerritorio.NEUTRO)
    )
    cenario_completo.sessao.flush()
    cenario_completo.coletar()

    for codigo in ("EH", "ZZ"):
        assert (
            montar_visto_do_pais(cenario_completo.sessao, codigo, cenario_completo.relogio) is None
        )
    assert "EH" not in por_codigo(mapa_de(cenario_completo))


# --------------------------------------------------------------------------- regra 3
def test_territorio_com_registro_proprio_usa_o_proprio_registro(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    lido_em = cenario_completo.relogio.agora()

    visto = visto_de(cenario_completo, "HK")

    assert visto.situacao is SituacaoDeVisto.ISENTO
    assert visto.origem is OrigemDoVisto.PROPRIO
    assert visto.soberano_nome is None
    assert visto.rotulo_original == "Visa not required"
    assert visto.dado_de == lido_em


def test_taiwan_tem_visto_proprio_e_nao_o_da_china(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()
    assert cenario_completo.requisito("TW") is not None

    taiwan = visto_de(cenario_completo, "TW")

    assert taiwan.origem is OrigemDoVisto.PROPRIO
    assert taiwan.situacao is SituacaoDeVisto.VISTO_EXIGIDO
    assert taiwan.soberano_nome is None


# --------------------------------------------------------------------------- regra 4
def test_dependencia_sem_registro_usa_o_soberano_e_diz_quem_e(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    reino_unido = cenario_completo.requisito("GB")
    assert reino_unido is not None
    assert cenario_completo.requisito("GG") is None  # Guernsey não tem linha própria

    visto = visto_de(cenario_completo, "GG")

    assert visto.origem is OrigemDoVisto.SOBERANO
    assert visto.soberano_nome == "Reino Unido"
    assert visto.situacao is SituacaoDeVisto.AUTORIZACAO_ELETRONICA
    assert visto.dado_de == reino_unido.lido_em
    assert visto.rotulo_original == reino_unido.rotulo_original
    # a dependência herdou também a permanência e o resto do que o soberano mostra
    assert visto.permanencia is not None
    assert (visto.permanencia.tipo, visto.permanencia.texto) == (
        TipoDePermanencia.PADRONIZADA,
        "6 meses",
    )


def test_porto_rico_sem_linha_propria_usa_os_estados_unidos(cenario_completo: "Cenario") -> None:
    cenario_completo.remover("Puerto Rico")
    cenario_completo.coletar()
    assert cenario_completo.requisito("PR") is None

    visto = visto_de(cenario_completo, "PR")

    assert visto.origem is OrigemDoVisto.SOBERANO
    assert visto.soberano_nome == "Estados Unidos"
    assert visto.situacao is SituacaoDeVisto.VISTO_EXIGIDO


def test_porto_rico_com_linha_propria_usa_a_propria(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()

    visto = visto_de(cenario_completo, "PR")

    assert visto.origem is OrigemDoVisto.PROPRIO
    assert visto.soberano_nome is None


# --------------------------------------------------------------------------- regra 2
# Kosovo e Malvinas têm a identidade da Sérvia e da Argentina no painel (001), mas a regra de
# entrada é a da linha própria da fonte: segue quem controla a fronteira. Nunca a do soberano.
def test_kosovo_usa_a_linha_propria_da_fonte_e_diz_a_que_territorio_se_refere(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.editar("Kosovo", rotulo="Visa required")  # difere da Sérvia (isenta)
    cenario_completo.coletar()
    proprio = cenario_completo.requisito("XK")
    assert proprio is not None

    kosovo = visto_de(cenario_completo, "XK")

    assert kosovo.situacao is SituacaoDeVisto.VISTO_EXIGIDO
    assert visto_de(cenario_completo, "RS").situacao is SituacaoDeVisto.ISENTO
    assert kosovo.rotulo_original == "Visa required"
    assert kosovo.origem is OrigemDoVisto.PROPRIO
    assert kosovo.soberano_nome is None  # sem nota de herança: o dado é dele
    assert kosovo.territorio_nome == "Kosovo"
    assert kosovo.dado_de == proprio.lido_em
    assert [o.texto_original for o in kosovo.observacoes] == ["90 days"]


def test_malvinas_usam_a_linha_propria_e_nunca_herdam_o_rg_da_argentina(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    argentina = visto_de(cenario_completo, "AR")
    assert argentina.aceita_rg is True

    malvinas = visto_de(cenario_completo, "FK")

    assert malvinas.aceita_rg is False
    assert malvinas.situacao is SituacaoDeVisto.ISENTO
    assert malvinas.origem is OrigemDoVisto.PROPRIO
    assert malvinas.soberano_nome is None
    assert malvinas.territorio_nome == "Ilhas Malvinas"
    assert malvinas.rotulo_original == "Visa not required"
    # a nota é a da linha das Malvinas, não a do RG da Argentina
    assert [o.texto_original for o in malvinas.observacoes] == [
        "A visitor permit is normally issued as a stamp in the passport on arrival, "
        "The maximum validity period is 1 month."
    ]


def test_malvinas_com_linha_propria_que_pede_visto_nao_ficam_isentas_como_a_argentina(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.editar("Falkland Islands", rotulo="Visa required")
    cenario_completo.coletar()

    assert visto_de(cenario_completo, "FK").situacao is SituacaoDeVisto.VISTO_EXIGIDO
    assert visto_de(cenario_completo, "AR").situacao is SituacaoDeVisto.ISENTO
    globo = por_codigo(mapa_de(cenario_completo))
    assert globo["FK"] == (SituacaoNoGlobo.VISTO_EXIGIDO, False)
    assert globo["AR"] == (SituacaoNoGlobo.ISENTO, True)


@pytest.mark.parametrize(
    ("codigo", "nome_na_fonte", "nome_no_visto", "soberano"),
    [("XK", "Kosovo", "Kosovo", "RS"), ("FK", "Falkland Islands", "Ilhas Malvinas", "AR")],
    ids=["kosovo", "malvinas"],
)
def test_sem_linha_propria_kosovo_e_malvinas_ficam_sem_informacao_e_nunca_com_o_soberano(
    cenario_completo: "Cenario", codigo: str, nome_na_fonte: str, nome_no_visto: str, soberano: str
) -> None:
    cenario_completo.remover(nome_na_fonte)
    cenario_completo.coletar()
    assert cenario_completo.requisito(codigo) is None
    assert cenario_completo.requisito(soberano) is not None  # o soberano tem dado, e não vale

    visto = visto_de(cenario_completo, codigo)

    assert visto.situacao is SituacaoDeVisto.SEM_INFORMACAO
    assert (visto.origem, visto.soberano_nome, visto.dado_de) == (None, None, None)
    assert visto.aceita_rg is False
    assert visto.territorio_nome == nome_no_visto  # a seção ainda diz de quem é
    assert por_codigo(mapa_de(cenario_completo))[codigo] == (SituacaoNoGlobo.SEM_INFORMACAO, False)


def test_no_globo_kosovo_e_malvinas_tem_a_situacao_da_propria_linha(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()

    globo = por_codigo(mapa_de(cenario_completo))

    assert globo["FK"] == (SituacaoNoGlobo.ISENTO, False)  # sem a variação de RG da Argentina
    assert globo["AR"] == (SituacaoNoGlobo.ISENTO, True)
    assert globo["XK"] == (SituacaoNoGlobo.ISENTO, False)


def test_as_malvinas_nunca_exibem_rg_nem_no_painel_nem_no_globo(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    # com a linha própria ou sem ela, a Argentina (que aceita RG) nunca empresta o RG
    for variante in ("com linha", "sem linha"):
        if variante == "sem linha":
            cenario_completo.sessao.delete(cenario_completo.requisito("FK"))
            cenario_completo.sessao.flush()
        assert visto_de(cenario_completo, "FK").aceita_rg is False, variante
        assert por_codigo(mapa_de(cenario_completo))["FK"][1] is False, variante
    assert visto_de(cenario_completo, "AR").aceita_rg is True  # a Argentina segue com RG


def test_so_kosovo_e_malvinas_dizem_a_que_territorio_a_secao_se_refere(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()

    nomes = {
        codigo: visto_de(cenario_completo, codigo).territorio_nome
        for codigo in ("AR", "RS", "GG", "HK", "TW", "PR", "SH", "XK", "FK")
    }

    assert nomes == {
        "AR": None,
        "RS": None,
        "GG": None,
        "HK": None,
        "TW": None,
        "PR": None,
        "SH": None,
        "XK": "Kosovo",
        "FK": "Ilhas Malvinas",
    }


# --------------------------------------------------------------------------- o que o registro diz
def test_campos_do_registro_chegam_a_visao(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()

    argentina = visto_de(cenario_completo, "AR")
    assert (argentina.situacao, argentina.aceita_rg) == (SituacaoDeVisto.ISENTO, True)
    assert argentina.permanencia is None  # a fonte não informa (FR-004)
    assert argentina.motivo_outra_situacao is None

    jamaica = visto_de(cenario_completo, "JM")
    assert jamaica.varia_conforme_motivo is True
    assert jamaica.permanencia is not None
    assert (jamaica.permanencia.tipo, jamaica.permanencia.texto) == (
        TipoDePermanencia.VARIA_CONFORME_MOTIVO,
        None,
    )

    etiopia = visto_de(cenario_completo, "ET")
    assert etiopia.permanencia is not None
    assert (etiopia.permanencia.tipo, etiopia.permanencia.texto) == (
        TipoDePermanencia.ORIGINAL,
        "up to 90 days",
    )

    santa_helena = visto_de(cenario_completo, "SH")
    assert santa_helena.situacao is SituacaoDeVisto.OUTRA_SITUACAO
    assert santa_helena.motivo_outra_situacao is not None
    assert santa_helena.motivo_outra_situacao.value == "rotulo_conhecido"
    assert santa_helena.rotulo_original == "Visa not required / eVisa / Permission required"


def test_as_observacoes_chegam_com_o_original_e_a_traducao(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()
    com_notas = next(r for r in cenario_completo.requisitos().values() if r.observacoes)

    visto = visto_de(cenario_completo, com_notas.territorio_codigo)

    assert [o.texto_original for o in visto.observacoes] == [
        o["texto"] for o in com_notas.observacoes
    ]
    assert all(o.traducao == f"[pt] {o.texto_original}" for o in visto.observacoes)


def test_sem_tradutor_a_observacao_chega_sem_traducao(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar(tradutor=None)
    com_notas = next(r for r in cenario_completo.requisitos().values() if r.observacoes)

    visto = visto_de(cenario_completo, com_notas.territorio_codigo)

    assert visto.observacoes
    assert all(o.traducao is None for o in visto.observacoes)


def test_a_fonte_e_sempre_o_artigo_da_wikipedia(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()
    visto = visto_de(cenario_completo, "US")
    mapa = mapa_de(cenario_completo)

    for fonte in (visto.fonte, mapa.fonte):
        assert (fonte.nome, fonte.url, fonte.licenca) == (
            NOME_DA_FONTE,
            URL_DO_ARTIGO,
            LICENCA_DA_FONTE,
        )


# --------------------------------------------------------------------------- regra 5
def test_antes_da_primeira_coleta_valida_tudo_e_sem_informacao(
    cenario_completo: "Cenario",
) -> None:
    visto = visto_de(cenario_completo, "AR")
    assert visto.situacao is SituacaoDeVisto.SEM_INFORMACAO
    assert (visto.rotulo_original, visto.permanencia, visto.origem, visto.dado_de) == (
        None,
        None,
        None,
        None,
    )
    assert (visto.aceita_rg, visto.varia_conforme_motivo, visto.desatualizado) == (
        False,
        False,
        False,
    )
    assert visto.observacoes == ()

    mapa = mapa_de(cenario_completo)
    assert (mapa.dados_obtidos, mapa.coletado_em, mapa.desatualizado) == (False, None, False)
    assert len(mapa.territorios) == TERRITORIOS_COM_PAINEL
    globo = por_codigo(mapa)
    assert globo.pop("BR") == (SituacaoNoGlobo.NAO_SE_APLICA, False)
    assert set(globo.values()) == {(SituacaoNoGlobo.SEM_INFORMACAO, False)}


def test_coleta_nao_valida_nao_conta_como_dado_obtido(cenario_completo: "Cenario") -> None:
    cenario_completo.wikipedia.falhar_com_status(503)
    assert not cenario_completo.servico().coletar().valida

    assert mapa_de(cenario_completo).dados_obtidos is False
    assert visto_de(cenario_completo, "AR").situacao is SituacaoDeVisto.SEM_INFORMACAO


def test_dependencia_sem_linha_e_com_soberano_sem_registro_fica_sem_informacao(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    assert cenario_completo.requisito("IM") is None  # Ilha de Man: sem linha própria...
    reino_unido = cenario_completo.requisito("GB")
    assert reino_unido is not None
    cenario_completo.sessao.delete(reino_unido)  # ...e sem o Reino Unido
    cenario_completo.sessao.flush()

    visto = visto_de(cenario_completo, "IM")

    assert visto.situacao is SituacaoDeVisto.SEM_INFORMACAO
    assert visto.origem is None
    assert visto.soberano_nome is None
    assert por_codigo(mapa_de(cenario_completo))["IM"] == (SituacaoNoGlobo.SEM_INFORMACAO, False)


def test_o_mapa_traz_um_item_por_territorio_com_painel_e_so_o_que_tem_dado_ganha_categoria(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    mapa = mapa_de(cenario_completo)
    globo = por_codigo(mapa)
    requisitos = cenario_completo.requisitos()

    assert mapa.dados_obtidos is True
    assert len(mapa.territorios) == TERRITORIOS_COM_PAINEL
    assert [t.codigo for t in mapa.territorios] == sorted(globo)
    for territorio in mapa.territorios:
        if territorio.codigo == "BR":
            assert territorio.situacao is SituacaoNoGlobo.NAO_SE_APLICA
        elif territorio.codigo in requisitos:
            assert territorio.situacao.value == requisitos[territorio.codigo].categoria.value
        elif territorio.situacao is not SituacaoNoGlobo.SEM_INFORMACAO:
            # SC-002: sem registro próprio, só o soberano de uma dependência comum dá categoria
            assert territorio.codigo in SEM_LINHA_PROPRIA


def test_o_rg_do_globo_vem_dos_oito_paises_da_fonte(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()

    com_rg = {c for c, (_, rg) in por_codigo(mapa_de(cenario_completo)).items() if rg}

    # os oito da fonte e mais ninguém: as Malvinas não herdam o RG da Argentina
    assert com_rg == {"AR", "BO", "CL", "CO", "EC", "PY", "PE", "UY"}


# --------------------------------------------------------------------------- datas
def test_dado_de_e_o_do_pais_e_nao_o_da_ultima_coleta_mesmo_com_mudanca_retida(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    primeira = cenario_completo.relogio.agora()
    cenario_completo.semana_seguinte()
    cenario_completo.editar("Algeria", rotulo="Visa not required")
    resumo = cenario_completo.coletar()
    segunda = cenario_completo.relogio.agora()
    assert [r.codigo for r in resumo.retidas] == ["DZ"]

    argelia = visto_de(cenario_completo, "DZ")
    argentina = visto_de(cenario_completo, "AR")

    assert argelia.situacao is SituacaoDeVisto.VISTO_EXIGIDO
    assert argelia.dado_de == primeira  # a data do dado exibido, não a da coleta que o reteve
    assert argentina.dado_de == segunda  # confirmada pela segunda coleta


@pytest.mark.parametrize(
    ("dias", "desatualizado"), [(14, False), (14.5, True), (15, True)], ids=["14d", "14d12h", "15d"]
)
def test_dado_com_mais_de_14_dias_e_desatualizado(
    cenario_completo: "Cenario", dias: float, desatualizado: bool
) -> None:
    cenario_completo.coletar()
    cenario_completo.relogio.avancar(days=dias)

    assert visto_de(cenario_completo, "AR").desatualizado is desatualizado
    assert mapa_de(cenario_completo).desatualizado is desatualizado


def test_pais_com_mudanca_retida_fica_desatualizado_antes_do_conjunto(
    cenario_completo: "Cenario",
) -> None:
    cenario_completo.coletar()
    cenario_completo.relogio.avancar(days=10)
    cenario_completo.editar("Algeria", rotulo="Visa not required")
    cenario_completo.coletar()
    cenario_completo.relogio.avancar(days=6)  # a Argélia tem 16 dias; a coleta, 6

    assert visto_de(cenario_completo, "DZ").desatualizado is True
    assert visto_de(cenario_completo, "AR").desatualizado is False
    assert mapa_de(cenario_completo).desatualizado is False


def test_coletado_em_e_o_fim_da_ultima_coleta_valida(cenario_completo: "Cenario") -> None:
    cenario_completo.coletar()
    primeira = cenario_completo.relogio.agora()
    cenario_completo.relogio.avancar(days=8)
    cenario_completo.wikipedia.falhar_com_status(503)
    assert not cenario_completo.servico().coletar().valida  # uma tentativa que falhou depois

    mapa = mapa_de(cenario_completo)

    assert mapa.coletado_em == primeira  # a que vale é a última VÁLIDA
    assert mapa.desatualizado is False
    assert visto_de(cenario_completo, "AR").dado_de == primeira


# --------------------------------------------------------------------------- consultas
def test_o_mapa_de_vistos_faz_tres_consultas_e_o_visto_do_painel_nao_passa_de_tres(
    cenario_completo: "Cenario", contar_consultas: "ContadorDeConsultas"
) -> None:
    cenario_completo.coletar()
    sessao, relogio = cenario_completo.sessao, cenario_completo.relogio

    with contar_consultas as contador:
        montar_vistos_do_mapa(sessao, relogio)
    assert contador.total == 3  # última coleta válida, territórios, registros

    for codigo in ("AR", "GG", "XK", "BR", "PR", "SH"):
        with contar_consultas as contador:
            montar_visto_do_pais(sessao, codigo, relogio)
        assert contador.total <= 3, codigo  # coleta válida, território e soberano, registros


def test_o_numero_de_consultas_nao_depende_da_quantidade_de_dados(
    cenario_completo: "Cenario", contar_consultas: "ContadorDeConsultas"
) -> None:
    sessao, relogio = cenario_completo.sessao, cenario_completo.relogio
    cenario_completo.coletar()
    with contar_consultas as contador:
        montar_vistos_do_mapa(sessao, relogio)
    com_dados = contador.total

    estados_unidos = cenario_completo.requisito("US")
    assert estados_unidos is not None
    sessao.delete(estados_unidos)
    sessao.flush()
    with contar_consultas as contador:
        montar_vistos_do_mapa(sessao, relogio)
    assert contador.total == com_dados
