"""`rotulos.yaml`: uma entrada por rótulo atômico aprovado (T038), cada uma com seu teste."""

import pytest

from farol.dominio import CategoriaDeVisto, MotivoOutraSituacao
from farol.vistos.dicionario import Dicionario
from farol.vistos.fonte import LinhaDaFonte
from farol.vistos.normalizacao import chave_de_consulta

ISENTO = CategoriaDeVisto.ISENTO
NA_CHEGADA = CategoriaDeVisto.VISTO_NA_CHEGADA
ELETRONICA = CategoriaDeVisto.AUTORIZACAO_ELETRONICA
EXIGIDO = CategoriaDeVisto.VISTO_EXIGIDO
OUTRA = CategoriaDeVisto.OUTRA_SITUACAO

# (chave normalizada, categoria, aceita_rg): os 20 rótulos atômicos de research.md 3.1
ROTULOS_APROVADOS = [
    ("visa not required", ISENTO, False),
    ("freedom of movement", ISENTO, True),
    ("visa on arrival", NA_CHEGADA, False),
    ("free visa on arrival", NA_CHEGADA, False),
    ("entry permit on arrival", NA_CHEGADA, False),
    ("free visitor's permit on arrival", NA_CHEGADA, False),
    ("evisa", ELETRONICA, False),
    ("electronic travel authorisation", ELETRONICA, False),
    ("electronic travel authorization", ELETRONICA, False),
    ("electronic travel authority", ELETRONICA, False),
    ("eta", ELETRONICA, False),
    ("e-voa", ELETRONICA, False),
    ("online visa", ELETRONICA, False),
    ("visa required", EXIGIDO, False),
    ("online visa required", EXIGIDO, False),
    ("permit required", OUTRA, False),
    ("special permit required", OUTRA, False),
    ("entry permit required", OUTRA, False),
    ("permission required", OUTRA, False),
    ("visa regime undefined", OUTRA, False),
]

# Rótulos cuja categoria vem da regra geral (O1): o motivo da entrada cita a regra
POR_REGRA_GERAL = [
    "online visa required",
    "e-voa",
    "online visa",
    "entry permit on arrival",
    "free visitor's permit on arrival",
]


def test_o_contrato_aprovado_tem_vinte_rotulos_distintos() -> None:
    chaves = [chave for chave, _, _ in ROTULOS_APROVADOS]
    assert len(chaves) == 20
    assert len(set(chaves)) == 20
    assert all(chave == chave_de_consulta(chave) for chave in chaves)


@pytest.mark.parametrize(("chave", "categoria", "aceita_rg"), ROTULOS_APROVADOS)
def test_entrada_do_rotulo(
    dicionario_real: Dicionario, chave: str, categoria: CategoriaDeVisto, aceita_rg: bool
) -> None:
    entrada = dicionario_real.rotulos[chave]
    assert entrada.categoria is categoria
    assert entrada.aceita_rg is aceita_rg


@pytest.mark.parametrize(("chave", "categoria", "aceita_rg"), ROTULOS_APROVADOS)
def test_rotulo_sozinho_e_classificado_pela_entrada(
    dicionario_real: Dicionario, chave: str, categoria: CategoriaDeVisto, aceita_rg: bool
) -> None:
    resultado = dicionario_real.classificar_rotulo(chave)
    assert resultado.categoria is categoria
    assert resultado.rotulo_para_revisao is None
    assert resultado.aceita_rg is False  # o RG exige também a nota (test_aceita_rg.py)
    if categoria is OUTRA:
        assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_CONHECIDO
    else:
        assert resultado.motivo_outra is None


def test_o_arquivo_nao_tem_entrada_fora_das_vinte(dicionario_real: Dicionario) -> None:
    aprovadas = {chave for chave, _, _ in ROTULOS_APROVADOS}
    assert set(dicionario_real.rotulos) == aprovadas


def test_so_freedom_of_movement_aceita_rg(dicionario_real: Dicionario) -> None:
    com_rg = {chave for chave, entrada in dicionario_real.rotulos.items() if entrada.aceita_rg}
    assert com_rg == {"freedom of movement"}


@pytest.mark.parametrize("chave", POR_REGRA_GERAL)
def test_motivo_cita_a_regra_geral_de_categoria(dicionario_real: Dicionario, chave: str) -> None:
    motivo = dicionario_real.rotulos[chave].motivo
    assert motivo, f"{chave}: falta o motivo da regra geral"


@pytest.mark.parametrize(("chave", "categoria", "aceita_rg"), ROTULOS_APROVADOS)
def test_exemplo_da_entrada_existe_na_fixture(
    dicionario_real: Dicionario,
    linhas_da_fonte: list[LinhaDaFonte],
    chave: str,
    categoria: CategoriaDeVisto,
    aceita_rg: bool,
) -> None:
    exemplo = dicionario_real.rotulos[chave].exemplo
    assert exemplo, f"{chave}: falta o exemplo"
    linhas = [linha for linha in linhas_da_fonte if linha.nome == exemplo]
    assert linhas, f"{chave}: {exemplo!r} não está na fixture"
    assert any(chave in chave_de_consulta(linha.rotulo).split(" / ") for linha in linhas)


def test_todo_rotulo_da_fixture_e_reconhecido(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    """SC-010: nenhum rótulo desconhecido na tabela atual."""
    distintos = {linha.rotulo for linha in linhas_da_fonte}
    assert len(distintos) >= 23
    desconhecidos = [
        rotulo
        for rotulo in distintos
        if dicionario_real.classificar_rotulo(rotulo).motivo_outra
        is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    ]
    assert desconhecidos == []


def test_rotulo_novo_continua_indo_para_revisao(dicionario_real: Dicionario) -> None:
    resultado = dicionario_real.classificar_rotulo("Visa waiver program")
    assert resultado.categoria is OUTRA
    assert resultado.motivo_outra is MotivoOutraSituacao.ROTULO_DESCONHECIDO
    assert resultado.rotulo_para_revisao == "visa waiver program"
