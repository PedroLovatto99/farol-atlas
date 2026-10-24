"""Regra do nível de cada território (data-model.md, "Regra do nível").

Função pura sobre linhas já carregadas: sem banco, sem relógio. O que chega aqui já é só o que
vale (alertas confirmados por coleta completa, com a classificação do hash confirmado).
"""

from datetime import UTC, datetime, timedelta

import pytest

from farol.dominio import NivelAlerta
from farol.mapa import (
    AlertaParaNivel,
    ItemDoAlerta,
    NivelExibido,
    NivelRegional,
    Regiao,
    RegiaoDoAlerta,
    TerritorioParaNivel,
    calcular_niveis,
    titulo_cita,
)

BASE = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def dia(n: int) -> datetime:
    return BASE + timedelta(days=n)


def pais(codigo: str, *nomes: str) -> TerritorioParaNivel:
    return TerritorioParaNivel(codigo, None, nomes or (codigo,))


def dependencia(codigo: str, soberano: str, *nomes: str) -> TerritorioParaNivel:
    return TerritorioParaNivel(codigo, soberano, nomes or (codigo,))


def item(
    territorio: str,
    nivel_pais: NivelAlerta | None = None,
    *regioes: tuple[str, NivelAlerta],
) -> ItemDoAlerta:
    return ItemDoAlerta(
        territorio, nivel_pais, tuple(RegiaoDoAlerta(nome, nivel) for nome, nivel in regioes)
    )


def alerta(
    numero: int, quando: datetime, *itens: ItemDoAlerta, titulo: str = ""
) -> AlertaParaNivel:
    return AlertaParaNivel(numero, titulo or f"Alerta {numero}", quando, itens)


def pendente(numero: int, quando: datetime, titulo: str) -> AlertaParaNivel:
    return AlertaParaNivel(numero, titulo, quando, None)


def nivel_de(
    codigo: str, territorios: list[TerritorioParaNivel], alertas: list[AlertaParaNivel]
) -> NivelExibido:
    return calcular_niveis(territorios, alertas, houve_coleta_completa=True)[codigo].nivel


EVITAR, NAO_VIAJAR, NORMALIZADA = (
    NivelAlerta.EVITAR,
    NivelAlerta.NAO_VIAJAR,
    NivelAlerta.NORMALIZADA,
)


# --------------------------------------------------------------------------- sem coleta completa
def test_nunca_houve_coleta_completa_todos_ficam_nao_verificados() -> None:
    resultado = calcular_niveis(
        [pais("BO"), pais("LB")],
        [alerta(1, dia(1), item("BO", NAO_VIAJAR))],
        houve_coleta_completa=False,
    )
    assert {c: n.nivel for c, n in resultado.items()} == {
        "BO": NivelExibido.NAO_VERIFICADO,
        "LB": NivelExibido.NAO_VERIFICADO,
    }
    assert all(n.regioes == () for n in resultado.values())


def test_devolve_um_resultado_para_cada_territorio() -> None:
    resultado = calcular_niveis([pais("BO"), pais("LB")], [], houve_coleta_completa=True)
    assert set(resultado) == {"BO", "LB"}


# --------------------------------------------------------------------------- sem alerta
def test_pais_que_ninguem_cita_esta_sem_alerta() -> None:
    assert (
        nivel_de("BO", [pais("BO")], [alerta(1, dia(1), item("LB", NAO_VIAJAR))])
        is NivelExibido.SEM_ALERTA
    )


def test_sem_nenhum_alerta_todos_estao_sem_alerta() -> None:
    assert nivel_de("BO", [pais("BO")], []) is NivelExibido.SEM_ALERTA


def test_alerta_que_nao_e_de_viagem_nao_afeta_ninguem() -> None:
    fraude = alerta(1, dia(5), titulo="Fraudes em nome dos consulados na Bolívia")  # sem itens
    assert nivel_de("BO", [pais("BO", "Bolívia")], [fraude]) is NivelExibido.SEM_ALERTA


# --------------------------------------------------------------------------- o mais recente vale
def test_vale_o_alerta_mais_recente_mesmo_que_um_antigo_seja_mais_grave() -> None:
    antigo = alerta(1, dia(1), item("BO", NAO_VIAJAR))
    recente = alerta(2, dia(30), item("BO", EVITAR))
    resultado = calcular_niveis([pais("BO")], [antigo, recente], houve_coleta_completa=True)
    assert resultado["BO"].nivel is NivelExibido.EVITAR
    assert resultado["BO"].alerta_id == 2


def test_a_ordem_dos_alertas_na_entrada_nao_importa() -> None:
    antigo = alerta(1, dia(1), item("BO", NAO_VIAJAR))
    recente = alerta(2, dia(30), item("BO", EVITAR))
    assert nivel_de("BO", [pais("BO")], [recente, antigo]) is NivelExibido.EVITAR


def test_normalizada_deixa_o_pais_sem_alerta_e_sem_regioes() -> None:
    antigo = alerta(1, dia(1), item("BO", NAO_VIAJAR, ("La Paz", NAO_VIAJAR)))
    bolivia_normalizada = alerta(2, dia(30), item("BO", NORMALIZADA, ("La Paz", EVITAR)))
    resultado = calcular_niveis(
        [pais("BO")], [antigo, bolivia_normalizada], houve_coleta_completa=True
    )
    assert resultado["BO"].nivel is NivelExibido.SEM_ALERTA
    assert resultado["BO"].regioes == ()
    assert resultado["BO"].regioes_em_destaque == ()


@pytest.mark.parametrize(
    ("nivel", "esperado"),
    [(EVITAR, NivelExibido.EVITAR), (NAO_VIAJAR, NivelExibido.NAO_VIAJAR)],
)
def test_nivel_do_pais_inteiro(nivel: NivelAlerta, esperado: NivelExibido) -> None:
    assert nivel_de("BO", [pais("BO")], [alerta(1, dia(1), item("BO", nivel))]) is esperado


# --------------------------------------------------------------------------- empate de datas
def test_empate_de_datas_vale_o_nivel_mais_grave() -> None:
    a = alerta(1, dia(5), item("BO", EVITAR))
    b = alerta(2, dia(5), item("BO", NAO_VIAJAR))
    assert nivel_de("BO", [pais("BO")], [a, b]) is NivelExibido.NAO_VIAJAR
    assert nivel_de("BO", [pais("BO")], [b, a]) is NivelExibido.NAO_VIAJAR


def test_empate_entre_normalizada_e_evitar_vale_evitar() -> None:
    a = alerta(1, dia(5), item("BO", NORMALIZADA))
    b = alerta(2, dia(5), item("BO", EVITAR))
    assert nivel_de("BO", [pais("BO")], [a, b]) is NivelExibido.EVITAR


# --------------------------------------------------------------------------- regiões
def test_so_regional_deixa_o_pais_sem_alerta_com_destaque_da_regiao() -> None:
    a = alerta(1, dia(1), item("PS", None, ("Faixa de Gaza", NAO_VIAJAR)))
    resultado = calcular_niveis([pais("PS")], [a], houve_coleta_completa=True)
    assert resultado["PS"].nivel is NivelExibido.SEM_ALERTA
    assert resultado["PS"].so_regional is True
    assert resultado["PS"].regioes == (Regiao("Faixa de Gaza", NivelRegional.NAO_VIAJAR),)
    assert resultado["PS"].regioes_em_destaque == resultado["PS"].regioes


def test_regiao_mais_grave_que_o_pais_tem_destaque() -> None:
    a = alerta(1, dia(1), item("LB", EVITAR, ("Sul do Líbano", NAO_VIAJAR)))
    resultado = calcular_niveis([pais("LB")], [a], houve_coleta_completa=True)
    assert resultado["LB"].nivel is NivelExibido.EVITAR
    assert resultado["LB"].so_regional is False
    assert resultado["LB"].regioes_em_destaque == (
        Regiao("Sul do Líbano", NivelRegional.NAO_VIAJAR),
    )


def test_regiao_tao_grave_quanto_o_pais_nao_tem_destaque_mas_continua_listada() -> None:
    a = alerta(1, dia(1), item("LB", NAO_VIAJAR, ("Sul do Líbano", NAO_VIAJAR), ("Norte", EVITAR)))
    resultado = calcular_niveis([pais("LB")], [a], houve_coleta_completa=True)
    assert resultado["LB"].nivel is NivelExibido.NAO_VIAJAR
    assert resultado["LB"].regioes_em_destaque == ()
    assert {r.nome for r in resultado["LB"].regioes} == {"Sul do Líbano", "Norte"}


def test_regioes_normalizadas_nao_aparecem() -> None:
    a = alerta(1, dia(1), item("LB", EVITAR, ("Sul do Líbano", NORMALIZADA), ("Norte", NAO_VIAJAR)))
    resultado = calcular_niveis([pais("LB")], [a], houve_coleta_completa=True)
    assert [r.nome for r in resultado["LB"].regioes] == ["Norte"]


def test_so_regional_com_todas_as_regioes_normalizadas_fica_limpo() -> None:
    a = alerta(1, dia(1), item("PS", None, ("Faixa de Gaza", NORMALIZADA)))
    resultado = calcular_niveis([pais("PS")], [a], houve_coleta_completa=True)
    assert resultado["PS"].nivel is NivelExibido.SEM_ALERTA
    assert resultado["PS"].regioes == ()
    assert resultado["PS"].so_regional is False


def test_alerta_mais_novo_substitui_as_regioes_do_antigo() -> None:
    antigo = alerta(1, dia(1), item("LB", EVITAR, ("Sul do Líbano", NAO_VIAJAR)))
    novo = alerta(2, dia(9), item("LB", EVITAR))
    resultado = calcular_niveis([pais("LB")], [antigo, novo], houve_coleta_completa=True)
    assert resultado["LB"].regioes == ()


# --------------------------------------------------------------------------- dependências (FR-031)
def test_dependencia_sem_alerta_proprio_segue_o_soberano() -> None:
    territorios = [pais("DK"), dependencia("GL", "DK")]
    a = alerta(1, dia(1), item("DK", EVITAR))
    assert nivel_de("GL", territorios, [a]) is NivelExibido.EVITAR


def test_dependencia_segue_o_soberano_quando_este_e_mais_recente() -> None:
    territorios = [pais("DK"), dependencia("GL", "DK")]
    marco_normalizada = alerta(1, dia(1), item("GL", NORMALIZADA))
    maio_nao_viaje = alerta(2, dia(60), item("DK", NAO_VIAJAR))
    assert (
        nivel_de("GL", territorios, [marco_normalizada, maio_nao_viaje]) is NivelExibido.NAO_VIAJAR
    )


def test_dependencia_segue_o_proprio_alerta_quando_este_e_mais_recente() -> None:
    territorios = [pais("DK"), dependencia("GL", "DK")]
    marco_nao_viaje = alerta(1, dia(1), item("DK", NAO_VIAJAR))
    maio_normalizada = alerta(2, dia(60), item("GL", NORMALIZADA))
    assert (
        nivel_de("GL", territorios, [marco_nao_viaje, maio_normalizada]) is NivelExibido.SEM_ALERTA
    )
    # o soberano não é afetado pelo alerta da dependência
    assert (
        nivel_de("DK", territorios, [marco_nao_viaje, maio_normalizada]) is NivelExibido.NAO_VIAJAR
    )


def test_soberano_nao_herda_o_alerta_da_dependencia() -> None:
    territorios = [pais("DK"), dependencia("GL", "DK")]
    assert (
        nivel_de("DK", territorios, [alerta(1, dia(1), item("GL", NAO_VIAJAR))])
        is NivelExibido.SEM_ALERTA
    )


def test_kosovo_como_dependencia_da_servia_segue_o_alerta_da_servia() -> None:
    territorios = [pais("RS", "Sérvia"), dependencia("XK", "RS", "Sérvia", "Kosovo")]
    assert (
        nivel_de("XK", territorios, [alerta(1, dia(1), item("RS", EVITAR))]) is NivelExibido.EVITAR
    )


# ------------------------------------------------------------------ alertas pendentes (FR-008)
def test_alerta_pendente_com_o_pais_no_titulo_deixa_o_pais_nao_verificado() -> None:
    p = pendente(1, dia(10), "Alerta de viagem – Bolívia")
    assert nivel_de("BO", [pais("BO", "Bolívia")], [p]) is NivelExibido.NAO_VERIFICADO


def test_pendente_mais_recente_que_um_alerta_classificado_vence() -> None:
    antigo = alerta(1, dia(1), item("BO", NORMALIZADA))
    p = pendente(2, dia(10), "Alerta de viagem – Bolívia")
    assert nivel_de("BO", [pais("BO", "Bolívia")], [antigo, p]) is NivelExibido.NAO_VERIFICADO


def test_pendente_mais_antigo_que_um_alerta_classificado_nao_atrapalha() -> None:
    p = pendente(1, dia(1), "Alerta de viagem – Bolívia")
    novo = alerta(2, dia(10), item("BO", EVITAR))
    assert nivel_de("BO", [pais("BO", "Bolívia")], [p, novo]) is NivelExibido.EVITAR


def test_pendente_na_mesma_data_de_um_classificado_vence_por_prudencia() -> None:
    p = pendente(1, dia(5), "Alerta – Bolívia")
    a = alerta(2, dia(5), item("BO", NORMALIZADA))
    assert nivel_de("BO", [pais("BO", "Bolívia")], [a, p]) is NivelExibido.NAO_VERIFICADO


def test_pendente_sem_pais_no_titulo_nao_muda_nada() -> None:
    p = pendente(1, dia(10), "Alerta Consular. Oriente Médio.")
    territorios = [pais("BO", "Bolívia"), pais("LB", "Líbano")]
    antigo = alerta(2, dia(1), item("BO", EVITAR))
    resultado = calcular_niveis(territorios, [antigo, p], houve_coleta_completa=True)
    assert resultado["BO"].nivel is NivelExibido.EVITAR
    assert resultado["LB"].nivel is NivelExibido.SEM_ALERTA


def test_dependencia_fica_nao_verificada_quando_o_titulo_pendente_cita_o_soberano() -> None:
    territorios = [pais("DK", "Dinamarca"), dependencia("GL", "DK", "Groenlândia")]
    p = pendente(1, dia(10), "Alerta – Dinamarca")
    assert nivel_de("GL", territorios, [p]) is NivelExibido.NAO_VERIFICADO


def test_dependencia_fica_nao_verificada_quando_o_titulo_pendente_cita_a_dependencia() -> None:
    territorios = [pais("DK", "Dinamarca"), dependencia("GL", "DK", "Groenlândia")]
    p = pendente(1, dia(10), "Alerta – Groenlândia")
    assert nivel_de("GL", territorios, [p]) is NivelExibido.NAO_VERIFICADO
    assert nivel_de("DK", territorios, [p]) is NivelExibido.SEM_ALERTA


# --------------------------------------------------------------------------- titulo_cita
@pytest.mark.parametrize(
    ("titulo", "nomes", "esperado"),
    [
        ("Alerta de viagem – Bolívia", ["Bolívia"], True),
        ("ALERTA DE VIAGEM - BOLIVIA", ["Bolívia"], True),
        ("Alerta Consular. Oriente Médio.", ["Bolívia", "Líbano"], False),
        ("Situação na Somália", ["Mali"], False),  # "mali" dentro de "somália" não conta
        ("Orientações aos Estados Unidos.", ["Estados Unidos"], True),
        ("República Democrática do Congo e Uganda", ["Uganda"], True),
        ("Alerta", [], False),
        ("Alerta – Kosovo", ["Sérvia", "Kosovo"], True),
    ],
)
def test_titulo_cita(titulo: str, nomes: list[str], esperado: bool) -> None:
    assert titulo_cita(titulo, nomes) is esperado
