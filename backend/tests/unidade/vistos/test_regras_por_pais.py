"""`regras_por_pais.yaml`: lista curada de países em que a regra ou o prazo varia por motivo."""

from farol.vistos.dicionario import Dicionario, calcular_hash_observacao
from farol.vistos.fonte import LinhaDaFonte


def _notas_do_codigo(dicionario: Dicionario, linhas: list[LinhaDaFonte], codigo: str) -> list[str]:
    return [linha.notas for linha in linhas if dicionario.ligar_nome(linha.nome).codigo == codigo]


def test_so_jamaica_e_zambia(dicionario_real: Dicionario) -> None:
    assert set(dicionario_real.regras) == {"JM", "ZM"}


def test_mexico_angola_e_libano_ficam_de_fora_de_proposito(dicionario_real: Dicionario) -> None:
    for codigo in ("MX", "AO", "LB"):
        assert codigo not in dicionario_real.regras


def test_as_duas_regras_valem_para_regra_e_prazo(dicionario_real: Dicionario) -> None:
    for codigo in ("JM", "ZM"):
        regra = dicionario_real.regras[codigo]
        assert regra.varia_conforme_motivo is True
        assert regra.prazos_diferem_por_motivo is True


def test_o_hash_de_cada_regra_bate_com_as_notas_da_fixture(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    for codigo, regra in dicionario_real.regras.items():
        notas = _notas_do_codigo(dicionario_real, linhas_da_fonte, codigo)
        assert any(notas), codigo
        assert calcular_hash_observacao(notas) == regra.hash_observacao, codigo


def test_uma_nota_alterada_nao_bate_mais_com_o_hash_guardado(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    notas = _notas_do_codigo(dicionario_real, linhas_da_fonte, "JM")
    alteradas = [nota.replace("6 months", "3 months") for nota in notas]
    assert alteradas != notas
    assert calcular_hash_observacao(alteradas) != dicionario_real.regras["JM"].hash_observacao


def test_a_nota_da_fixture_cita_os_dois_motivos(
    dicionario_real: Dicionario, linhas_da_fonte: list[LinhaDaFonte]
) -> None:
    for codigo in ("JM", "ZM"):
        texto = " ".join(_notas_do_codigo(dicionario_real, linhas_da_fonte, codigo)).casefold()
        assert "business" in texto, codigo
        assert "touris" in texto, codigo  # "tourist" (Jamaica) e "Tourists"/"tourism" (Zâmbia)
