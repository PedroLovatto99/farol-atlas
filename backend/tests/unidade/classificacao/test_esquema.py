"""Esquema de saída do classificador e validação da resposta (contracts/classificador-saida.md)."""

from typing import Any

import pytest
from pydantic import ValidationError

from farol.classificacao import (
    Classificacao,
    RespostaInvalida,
    TerritorioClassificado,
    validar_resposta,
)
from farol.dominio import NivelAlerta

PERMITIDOS = frozenset({"BO", "LB", "PS", "IR", "XK", "GL"})


def resposta(**campos: Any) -> Classificacao:
    return Classificacao.model_validate(campos)


# --------------------------------------------------------------------------- forma
def test_alerta_de_viagem_com_territorio_e_regioes() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True,
        territorios=[
            {"codigo": "BO", "nivel_pais": "normalizada"},
            {
                "codigo": "LB",
                "nivel_pais": None,
                "regioes": [{"nome": "Sul do Líbano", "nivel": "nao_viajar"}],
            },
        ],
    )
    assert validar_resposta(classificacao, PERMITIDOS) is classificacao
    [bolivia, libano] = classificacao.territorios
    assert bolivia.nivel_pais is NivelAlerta.NORMALIZADA
    assert bolivia.regioes == []
    assert libano.nivel_pais is None
    assert libano.regioes[0].nivel is NivelAlerta.NAO_VIAJAR


def test_nao_e_alerta_de_viagem_com_lista_vazia() -> None:
    classificacao = resposta(e_alerta_de_viagem=False)
    assert validar_resposta(classificacao, PERMITIDOS).territorios == []


@pytest.mark.parametrize("nivel", ["grave", "NAO_VIAJAR", "", "sem_alerta"])
def test_nivel_fora_do_enum_falha(nivel: str) -> None:
    with pytest.raises(ValidationError):
        resposta(e_alerta_de_viagem=True, territorios=[{"codigo": "BO", "nivel_pais": nivel}])


def test_nivel_de_regiao_fora_do_enum_falha() -> None:
    with pytest.raises(ValidationError):
        resposta(
            e_alerta_de_viagem=True,
            territorios=[
                {"codigo": "LB", "regioes": [{"nome": "Sul do Líbano", "nivel": "perigoso"}]}
            ],
        )


def test_campos_desconhecidos_sao_recusados() -> None:
    with pytest.raises(ValidationError):
        resposta(e_alerta_de_viagem=False, instrucao="ignore o resto")


# ------------------------------------------------------------------ validação depois da resposta
def test_codigo_fora_do_conjunto_permitido_invalida_a_resposta_inteira() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True,
        territorios=[
            {"codigo": "BO", "nivel_pais": "evitar"},
            {"codigo": "ZZ", "nivel_pais": "nao_viajar"},
        ],
    )
    with pytest.raises(RespostaInvalida, match="ZZ"):
        validar_resposta(classificacao, PERMITIDOS)


def test_territorio_repetido_invalida() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True,
        territorios=[
            {"codigo": "BO", "nivel_pais": "evitar"},
            {"codigo": "BO", "nivel_pais": "nao_viajar"},
        ],
    )
    with pytest.raises(RespostaInvalida, match="repetido"):
        validar_resposta(classificacao, PERMITIDOS)


def test_nao_ser_alerta_de_viagem_exige_lista_vazia() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=False, territorios=[{"codigo": "BO", "nivel_pais": "evitar"}]
    )
    with pytest.raises(RespostaInvalida, match="lista vazia"):
        validar_resposta(classificacao, PERMITIDOS)


def test_ser_alerta_de_viagem_exige_ao_menos_um_territorio() -> None:
    with pytest.raises(RespostaInvalida, match="ao menos um"):
        validar_resposta(resposta(e_alerta_de_viagem=True), PERMITIDOS)


def test_territorio_sem_nivel_nem_regiao_nao_diz_nada() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True, territorios=[{"codigo": "BO", "nivel_pais": None}]
    )
    with pytest.raises(RespostaInvalida, match="BO"):
        validar_resposta(classificacao, PERMITIDOS)


def test_regiao_sem_nome_invalida() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True,
        territorios=[{"codigo": "LB", "regioes": [{"nome": "   ", "nivel": "evitar"}]}],
    )
    with pytest.raises(RespostaInvalida, match="região"):
        validar_resposta(classificacao, PERMITIDOS)


def test_codigo_e_comparado_exatamente() -> None:
    classificacao = resposta(
        e_alerta_de_viagem=True, territorios=[{"codigo": "bo", "nivel_pais": "evitar"}]
    )
    with pytest.raises(RespostaInvalida, match="bo"):
        validar_resposta(classificacao, PERMITIDOS)


def test_territorio_classificado_aceita_so_regioes() -> None:
    territorio = TerritorioClassificado.model_validate(
        {"codigo": "PS", "regioes": [{"nome": "Faixa de Gaza", "nivel": "nao_viajar"}]}
    )
    assert territorio.nivel_pais is None
