"""Trava: o contrato da 002 preserva tudo o que o da 001 já prometia.

Lê `specs/001-mapa-alertas-viagem/contracts/openapi.yaml` e
`specs/002-visto-brasileiros/contracts/openapi.yaml` e falha se, em relação à 001:

- uma rota ou uma operação sumir ou mudar (identificador, parâmetros, respostas);
- um esquema sumir ou mudar;
- uma propriedade existente sumir, mudar de tipo ou deixar de ser obrigatória;
- aparecer qualquer propriedade nova fora da lista aprovada (`PROPRIEDADES_APROVADAS`).

Rotas novas (`/vistos`) e esquemas novos são permitidos. Os testes da própria trava usam cópias em
memória dos dois documentos, alteradas de propósito: cada alteração **tem de** ser apontada.
"""

import copy
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from tests.contrato.conftest import Normalizacao

Documento = dict[str, Any]

RAIZ_SPECS = Path(__file__).resolve().parents[3] / "specs"
CONTRATO_001 = RAIZ_SPECS / "001-mapa-alertas-viagem" / "contracts" / "openapi.yaml"
CONTRATO_002 = RAIZ_SPECS / "002-visto-brasileiros" / "contracts" / "openapi.yaml"

# Esquema -> propriedades novas aprovadas (e que têm de ser obrigatórias). Hoje só `Pais.visto`.
PROPRIEDADES_APROVADAS: dict[str, frozenset[str]] = {"Pais": frozenset({"visto"})}


def resumo_da_operacao(operacao: Documento, esboco: Callable[[Documento], Documento]) -> Documento:
    """O que é contrato numa operação: identificador, parâmetros e respostas (sem textos)."""
    parametros = {
        (p["name"], p["in"]): {
            "obrigatorio": p.get("required", False),
            "schema": esboco(p["schema"]),
            "padrao": p["schema"].get("pattern"),
        }
        for p in operacao.get("parameters", [])
    }
    respostas = {
        codigo: {
            tipo: esboco(conteudo["schema"])
            for tipo, conteudo in resposta.get("content", {}).items()
        }
        for codigo, resposta in operacao.get("responses", {}).items()
    }
    return {
        "operationId": operacao.get("operationId"),
        "parametros": parametros,
        "respostas": respostas,
    }


def violacoes(
    antigo: Documento,
    novo: Documento,
    esboco: Callable[[Documento], Documento],
    aprovadas: dict[str, frozenset[str]] = PROPRIEDADES_APROVADAS,
) -> list[str]:
    """Tudo o que o contrato `novo` quebra em relação ao `antigo` (vazio = preservou)."""
    achados: list[str] = []

    if antigo.get("servers") != novo.get("servers"):
        achados.append("servers: mudou")

    # ------------------------------------------------------------------ rotas e operações
    for caminho, rota in antigo["paths"].items():
        if caminho not in novo["paths"]:
            achados.append(f"rota removida: {caminho}")
            continue
        rota_nova = novo["paths"][caminho]
        for metodo, operacao in rota.items():
            if metodo not in rota_nova:
                achados.append(f"operação removida: {metodo.upper()} {caminho}")
            elif resumo_da_operacao(operacao, esboco) != resumo_da_operacao(
                rota_nova[metodo], esboco
            ):
                achados.append(
                    f"operação mudou (parâmetro ou resposta): {metodo.upper()} {caminho}"
                )
        for metodo in rota_nova:
            if metodo not in rota:
                achados.append(f"operação nova numa rota da 001: {metodo.upper()} {caminho}")

    # ------------------------------------------------------------------ esquemas
    esquemas_novos = novo.get("components", {}).get("schemas", {})
    for nome, esquema in antigo.get("components", {}).get("schemas", {}).items():
        if nome not in esquemas_novos:
            achados.append(f"esquema removido: {nome}")
            continue
        achados += violacoes_do_esquema(
            nome, esboco(esquema), esboco(esquemas_novos[nome]), aprovadas.get(nome, frozenset())
        )
    return achados


def violacoes_do_esquema(
    nome: str, antigo: Documento, novo: Documento, aprovadas: frozenset[str]
) -> list[str]:
    achados: list[str] = []
    propriedades_antigas: dict[str, Documento] = antigo.get("propriedades", {})
    propriedades_novas: dict[str, Documento] = novo.get("propriedades", {})

    resto_antigo = {k: v for k, v in antigo.items() if k not in ("propriedades", "obrigatorios")}
    resto_novo = {k: v for k, v in novo.items() if k not in ("propriedades", "obrigatorios")}
    if resto_antigo != resto_novo:
        achados.append(f"esquema mudou: {nome}")

    for propriedade, definicao in propriedades_antigas.items():
        if propriedade not in propriedades_novas:
            achados.append(f"propriedade removida: {nome}.{propriedade}")
        elif propriedades_novas[propriedade] != definicao:
            achados.append(f"propriedade mudou de tipo: {nome}.{propriedade}")

    deixaram_de_ser_obrigatorias = set(antigo.get("obrigatorios", [])) - set(
        novo.get("obrigatorios", [])
    )
    for propriedade in sorted(deixaram_de_ser_obrigatorias):
        achados.append(f"propriedade deixou de ser obrigatória: {nome}.{propriedade}")

    for propriedade in sorted(set(propriedades_novas) - set(propriedades_antigas)):
        if propriedade not in aprovadas:
            achados.append(f"propriedade nova fora da lista aprovada: {nome}.{propriedade}")
        elif propriedade not in novo.get("obrigatorios", []):
            achados.append(f"propriedade nova aprovada, mas não obrigatória: {nome}.{propriedade}")
    return achados


# --------------------------------------------------------------------------- os contratos reais
@pytest.fixture(scope="module")
def contrato_001() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO_001.read_text(encoding="utf-8"))
    return carregado


@pytest.fixture(scope="module")
def contrato_002() -> Documento:
    carregado: Documento = yaml.safe_load(CONTRATO_002.read_text(encoding="utf-8"))
    return carregado


def test_a_002_preserva_tudo_o_que_a_001_prometia(
    contrato_001: Documento, contrato_002: Documento, normalizacao: "Normalizacao"
) -> None:
    assert violacoes(contrato_001, contrato_002, normalizacao.esboco) == []


def test_a_unica_propriedade_nova_e_pais_visto_e_ela_e_obrigatoria(
    contrato_001: Documento, contrato_002: Documento, normalizacao: "Normalizacao"
) -> None:
    antigos = contrato_001["components"]["schemas"]
    novos = contrato_002["components"]["schemas"]
    acrescentadas = {
        nome: sorted(set(novos[nome]["properties"]) - set(esquema.get("properties", {})))
        for nome, esquema in antigos.items()
        if set(novos[nome].get("properties", {})) - set(esquema.get("properties", {}))
    }
    assert acrescentadas == {"Pais": ["visto"]}
    assert "visto" in normalizacao.esboco(novos["Pais"])["obrigatorios"]


def test_rota_e_esquemas_novos_sao_permitidos(
    contrato_001: Documento, contrato_002: Documento, normalizacao: "Normalizacao"
) -> None:
    assert set(contrato_002["paths"]) - set(contrato_001["paths"]) == {"/vistos"}
    novos = set(contrato_002["components"]["schemas"]) - set(contrato_001["components"]["schemas"])
    assert novos  # a 002 acrescenta esquemas, e isso não é violação
    assert violacoes(contrato_001, contrato_002, normalizacao.esboco) == []


# --------------------------------------------------------------------------- testes da trava
Alteracao = Callable[[Documento], None]


def remover_rota(doc: Documento) -> None:
    del doc["paths"]["/mapa"]


def remover_operacao(doc: Documento) -> None:
    del doc["paths"]["/saude"]["get"]


def mudar_operation_id(doc: Documento) -> None:
    doc["paths"]["/mapa"]["get"]["operationId"] = "outraCoisa"


def mudar_parametro(doc: Documento) -> None:
    doc["paths"]["/paises/{codigo}"]["get"]["parameters"][0]["schema"] = {"type": "integer"}


def mudar_padrao_do_parametro(doc: Documento) -> None:
    doc["paths"]["/paises/{codigo}"]["get"]["parameters"][0]["schema"]["pattern"] = "^.*$"


def acrescentar_parametro(doc: Documento) -> None:
    doc["paths"]["/mapa"]["get"]["parameters"] = [
        {"name": "filtro", "in": "query", "required": False, "schema": {"type": "string"}}
    ]


def remover_resposta(doc: Documento) -> None:
    del doc["paths"]["/paises/{codigo}"]["get"]["responses"]["404"]


def mudar_esquema_da_resposta(doc: Documento) -> None:
    resposta = doc["paths"]["/mapa"]["get"]["responses"]["200"]
    resposta["content"]["application/json"]["schema"] = {"$ref": "#/components/schemas/Erro"}


def remover_esquema(doc: Documento) -> None:
    del doc["components"]["schemas"]["Saude"]


def remover_propriedade(doc: Documento) -> None:
    del doc["components"]["schemas"]["Pais"]["properties"]["nome"]


def trocar_tipo_da_propriedade(doc: Documento) -> None:
    doc["components"]["schemas"]["Pais"]["properties"]["nome"] = {"type": "integer"}


def tornar_anulavel(doc: Documento) -> None:
    doc["components"]["schemas"]["Pais"]["properties"]["nome"] = {"type": ["string", "null"]}


def deixar_de_ser_obrigatoria(doc: Documento) -> None:
    doc["components"]["schemas"]["Pais"]["required"].remove("nome")


def mudar_enum(doc: Documento) -> None:
    esquema = doc["components"]["schemas"]["Nivel"]
    esquema["enum"] = [*esquema["enum"], "novo_nivel"]


def propriedade_nova_em_pais(doc: Documento) -> None:
    doc["components"]["schemas"]["Pais"]["properties"]["novidade"] = {"type": "string"}


def propriedade_nova_em_outro_esquema(doc: Documento) -> None:
    doc["components"]["schemas"]["Mapa"]["properties"]["novidade"] = {"type": "string"}


def visto_deixa_de_ser_obrigatorio(doc: Documento) -> None:
    doc["components"]["schemas"]["Pais"]["required"].remove("visto")


ALTERACOES_QUE_TEM_DE_FALHAR: list[tuple[str, Alteracao]] = [
    ("rota removida", remover_rota),
    ("operação removida", remover_operacao),
    ("operationId mudado", mudar_operation_id),
    ("parâmetro mudado", mudar_parametro),
    ("padrão do parâmetro mudado", mudar_padrao_do_parametro),
    ("parâmetro novo numa rota da 001", acrescentar_parametro),
    ("resposta removida", remover_resposta),
    ("esquema da resposta mudado", mudar_esquema_da_resposta),
    ("esquema removido", remover_esquema),
    ("propriedade removida", remover_propriedade),
    ("tipo trocado", trocar_tipo_da_propriedade),
    ("propriedade passou a aceitar nulo", tornar_anulavel),
    ("propriedade deixou de ser obrigatória", deixar_de_ser_obrigatoria),
    ("enum mudado", mudar_enum),
    ("propriedade nova qualquer em Pais", propriedade_nova_em_pais),
    ("propriedade nova qualquer em outro esquema", propriedade_nova_em_outro_esquema),
    ("Pais.visto deixa de ser obrigatório", visto_deixa_de_ser_obrigatorio),
]


@pytest.mark.parametrize(
    "alterar",
    [a for _, a in ALTERACOES_QUE_TEM_DE_FALHAR],
    ids=[n for n, _ in ALTERACOES_QUE_TEM_DE_FALHAR],
)
def test_a_trava_aponta_a_alteracao(
    alterar: Alteracao,
    contrato_001: Documento,
    contrato_002: Documento,
    normalizacao: "Normalizacao",
) -> None:
    alterado = copy.deepcopy(contrato_002)
    alterar(alterado)
    assert violacoes(contrato_001, alterado, normalizacao.esboco) != []


def test_a_trava_aponta_a_propriedade_removida_pelo_nome(
    contrato_001: Documento, contrato_002: Documento, normalizacao: "Normalizacao"
) -> None:
    alterado = copy.deepcopy(contrato_002)
    remover_propriedade(alterado)
    assert violacoes(contrato_001, alterado, normalizacao.esboco) == [
        "propriedade removida: Pais.nome"
    ]


def test_a_trava_nao_se_assusta_com_rota_e_esquema_novos(
    contrato_001: Documento, contrato_002: Documento, normalizacao: "Normalizacao"
) -> None:
    alterado = copy.deepcopy(contrato_002)
    alterado["paths"]["/outra-rota-nova"] = copy.deepcopy(alterado["paths"]["/vistos"])
    alterado["components"]["schemas"]["EsquemaNovo"] = {"type": "object", "properties": {}}
    assert violacoes(contrato_001, alterado, normalizacao.esboco) == []


def test_a_trava_aceita_so_a_propriedade_aprovada(
    contrato_001: Documento, normalizacao: "Normalizacao"
) -> None:
    """Contra a própria 001, a lista aprovada sozinha não basta: sem `Pais.visto` obrigatório."""
    com_visto = copy.deepcopy(contrato_001)
    pais = com_visto["components"]["schemas"]["Pais"]
    pais["properties"]["visto"] = {"type": ["object", "null"]}
    assert violacoes(contrato_001, com_visto, normalizacao.esboco) == [
        "propriedade nova aprovada, mas não obrigatória: Pais.visto"
    ]
    pais["required"].append("visto")
    assert violacoes(contrato_001, com_visto, normalizacao.esboco) == []
