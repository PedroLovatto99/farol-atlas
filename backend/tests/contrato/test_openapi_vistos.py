"""`/vistos`, `Pais.visto` e os esquemas de visto equivalem ao contrato em specs/.../contracts.

A normalização (tipos, anulabilidade, enums, referências) está em `conftest.py`.
"""

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

CAMINHO = "/vistos"
ESQUEMAS_DE_VISTO = (
    "Visto",
    "VistosDoMapa",
    "TerritorioDeVisto",
    "Permanencia",
    "ObservacaoDeVisto",
    "SituacaoDeVisto",
    "SituacaoNoGlobo",
    "MotivoOutraSituacao",
    "OrigemDoVisto",
    "TipoDePermanencia",
)


def test_rota_de_vistos_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperada = contrato["paths"][CAMINHO]["get"]
    rota = gerado["paths"][f"{normalizacao.prefixo}{CAMINHO}"]
    obtida = rota["get"]

    assert set(rota) == {"get"}  # só leitura
    assert obtida["operationId"] == esperada["operationId"] == "obterVistos"
    assert set(obtida["responses"]) >= set(esperada["responses"])
    assert normalizacao.resposta_200(obtida) == normalizacao.resposta_200(esperada)
    assert normalizacao.resposta_200(obtida) == "VistosDoMapa"
    assert not obtida.get("parameters")  # sem parâmetros: a rota devolve tudo de uma vez


@pytest.mark.parametrize("nome", ESQUEMAS_DE_VISTO)
def test_cada_esquema_de_visto_equivale_ao_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao", nome: str
) -> None:
    esperado = contrato["components"]["schemas"][nome]
    obtido = gerado["components"]["schemas"][nome]

    assert normalizacao.esboco(obtido) == normalizacao.esboco(esperado), (
        f"schema {nome} difere do contrato"
    )


def test_os_esquemas_alcancados_pela_rota_sao_os_do_contrato(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    esperado = normalizacao.fecho("VistosDoMapa", contrato["components"]["schemas"])
    obtido = normalizacao.fecho("VistosDoMapa", gerado["components"]["schemas"])

    assert set(obtido) == set(esperado)
    assert {"SituacaoNoGlobo", "TerritorioDeVisto", "Fonte"} <= set(obtido)
    for nome in sorted(esperado):
        assert obtido[nome] == esperado[nome], f"schema {nome} difere do contrato"


def test_o_visto_do_painel_alcanca_os_esquemas_esperados(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    for documento in (contrato, gerado):
        assert set(normalizacao.fecho("Visto", documento["components"]["schemas"])) == {
            "Visto",
            "SituacaoDeVisto",
            "MotivoOutraSituacao",
            "Permanencia",
            "TipoDePermanencia",
            "ObservacaoDeVisto",
            "OrigemDoVisto",
            "Fonte",
        }


def test_pais_visto_e_anulavel_e_obrigatorio(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    for documento in (contrato, gerado):
        pais = normalizacao.esboco(documento["components"]["schemas"]["Pais"])
        assert "visto" in pais["obrigatorios"]
        assert pais["propriedades"]["visto"] == {"ref": "Visto", "anulavel": True}


def test_os_enums_de_visto_tem_exatamente_os_valores_do_contrato(gerado: Documento) -> None:
    esquemas = gerado["components"]["schemas"]
    base = {
        "isento",
        "visto_na_chegada",
        "autorizacao_eletronica",
        "visto_exigido",
        "outra_situacao",
        "sem_informacao",
    }
    assert set(esquemas["SituacaoDeVisto"]["enum"]) == base
    assert set(esquemas["SituacaoNoGlobo"]["enum"]) == base | {"nao_se_aplica"}
    assert set(esquemas["MotivoOutraSituacao"]["enum"]) == {
        "rotulo_conhecido",
        "rotulo_desconhecido",
    }
    assert set(esquemas["OrigemDoVisto"]["enum"]) == {"proprio", "soberano"}
    assert set(esquemas["TipoDePermanencia"]["enum"]) == {
        "padronizada",
        "original",
        "prazos_divergentes",
        "varia_conforme_motivo",
    }


def test_visto_tem_territorio_nome_anulavel_e_obrigatorio(
    contrato: Documento, gerado: Documento, normalizacao: "Normalizacao"
) -> None:
    for documento in (contrato, gerado):
        visto = normalizacao.esboco(documento["components"]["schemas"]["Visto"])
        assert "territorio_nome" in visto["obrigatorios"]
        assert visto["propriedades"]["territorio_nome"] == {"tipos": ["string"], "anulavel": True}
