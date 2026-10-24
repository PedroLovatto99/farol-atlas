"""Artefatos gerados por scripts/gerar_geometria.py, conforme contracts/geometria-territorios.md.

Testam os arquivos versionados (a geometria do frontend e o seed de territórios), sem precisar do
Natural Earth: se alguém regerar a geometria e quebrar uma regra do mapa, estes testes falham.
"""

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parents[4]
GEOJSON = RAIZ / "frontend" / "public" / "geo" / "territorios.geojson"
SEED = RAIZ / "dados" / "territorios" / "territorios.json"
POSTOS = RAIZ / "dados" / "postos"
LIMITE_DE_BYTES = 1_500_000
# Entradas da lista do Itamaraty que o mapa desenha como dependência de outro país
DEPENDENCIAS_NA_LISTA = {"TW", "GF", "PR"}


def _csv(nome: str) -> list[dict[str, str]]:
    with (POSTOS / nome).open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


@pytest.fixture(scope="module")
def itamaraty() -> set[str]:
    """Os 198 da lista do Itamaraty: países com posto, atendidos por outro posto e o Brasil."""
    codigos = {linha["pais_iso"] for linha in _csv("postos_brasileiros.csv")}
    codigos |= {linha["pais_iso"] for linha in _csv("jurisdicao_cumulativa.csv")}
    return codigos | {"BR"}


@pytest.fixture(scope="module")
def feicoes() -> list[dict[str, Any]]:
    conteudo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    feicoes: list[dict[str, Any]] = conteudo["features"]
    return feicoes


@pytest.fixture(scope="module")
def seed() -> dict[str, Any]:
    conteudo: dict[str, Any] = json.loads(SEED.read_text(encoding="utf-8"))
    return conteudo


def _propriedades(feicoes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [f["properties"] for f in feicoes]


def test_a_lista_do_itamaraty_tem_198_paises(itamaraty: set[str]) -> None:
    assert len(itamaraty) == 198


def test_todo_pais_do_itamaraty_esta_desenhado(
    feicoes: list[dict[str, Any]], itamaraty: set[str]
) -> None:
    desenhados = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "pais"}
    # Taiwan (FR-033), Guiana Francesa (FR-031) e Porto Rico: na lista, mas desenhados como
    # dependências
    assert itamaraty - DEPENDENCIAS_NA_LISTA - desenhados == set()
    dependencias = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "dependencia"}
    assert dependencias >= DEPENDENCIAS_NA_LISTA


def test_todo_territorio_do_mapa_e_pais_da_lista_dependencia_ou_area_neutra(
    feicoes: list[dict[str, Any]], itamaraty: set[str], seed: dict[str, Any]
) -> None:
    """Nenhum território aparece como país independente se não estiver na lista do Itamaraty."""
    paises_da_lista = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "pais"}
    na_lista_do_seed = {d["codigo"] for d in seed["dependencias"] if d["na_lista_itamaraty"]}

    for p in _propriedades(feicoes):
        codigo, tipo = p["codigo"], p["tipo"]
        if tipo == "pais":
            assert codigo in itamaraty, f"{codigo} aparece como país fora da lista do Itamaraty"
            assert p["soberano"] is None, p
        elif tipo == "dependencia":
            assert p["soberano"] in itamaraty, f"{codigo}: soberano {p['soberano']} fora da lista"
            assert p["soberano"] in paises_da_lista, f"{codigo}: soberano não é um país do mapa"
        else:
            assert tipo == "neutro", p
            assert codigo not in itamaraty, f"{codigo} está na lista do Itamaraty e é neutro"
            assert p["soberano"] is None, p

    # uma entrada da lista que o mapa desenha como dependência é marcada como tal no seed
    dependencias = {d["codigo"] for d in seed["dependencias"]}
    assert na_lista_do_seed == dependencias & itamaraty


def test_nenhum_pais_ou_dependencia_fora_do_seed(
    feicoes: list[dict[str, Any]], itamaraty: set[str], seed: dict[str, Any]
) -> None:
    dependencias = {d["codigo"] for d in seed["dependencias"]}
    conhecidos = itamaraty | dependencias
    for p in _propriedades(feicoes):
        if p["tipo"] in {"pais", "dependencia"}:
            assert p["codigo"] in conhecidos, p
    # e o contrário: toda dependência do seed está desenhada
    desenhados = {p["codigo"] for p in _propriedades(feicoes)}
    assert dependencias - desenhados == set()


def test_codigos_das_feicoes_de_pais_e_dependencia_nao_se_repetem_entre_tipos(
    feicoes: list[dict[str, Any]],
) -> None:
    dependencias = [p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "dependencia"]
    assert len(dependencias) == len(set(dependencias))
    paises = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "pais"}
    assert paises.isdisjoint(dependencias)


def test_soberano_existe_e_e_pais(feicoes: list[dict[str, Any]]) -> None:
    paises = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "pais"}
    for p in _propriedades(feicoes):
        if p["tipo"] == "dependencia":
            assert p["soberano"] in paises, p


@pytest.mark.parametrize(
    ("codigo", "soberano"), [("FK", "AR"), ("XK", "RS")], ids=["malvinas", "kosovo"]
)
def test_malvinas_e_kosovo_sao_dependencias_com_o_zoom_do_soberano(
    feicoes: list[dict[str, Any]], codigo: str, soberano: str
) -> None:
    [p] = [p for p in _propriedades(feicoes) if p["codigo"] == codigo]
    assert p["tipo"] == "dependencia"
    assert p["soberano"] == soberano
    assert p["zoom"] == soberano


def test_areas_neutras(feicoes: list[dict[str, Any]]) -> None:
    neutros = {p["codigo"] for p in _propriedades(feicoes) if p["tipo"] == "neutro"}
    assert {"EH", "AQ"} <= neutros
    assert "FK" not in neutros


def test_taiwan_e_dependencia_da_china_sem_bandeira(
    feicoes: list[dict[str, Any]], seed: dict[str, Any]
) -> None:
    [p] = [p for p in _propriedades(feicoes) if p["codigo"] == "TW"]
    assert p["tipo"] == "dependencia"
    assert p["soberano"] == "CN"
    assert p["titulo"] == "Taiwan (China)"
    [d] = [d for d in seed["dependencias"] if d["codigo"] == "TW"]
    assert d["codigo_bandeira"] is None


def test_guiana_francesa_e_separada_da_franca(feicoes: list[dict[str, Any]]) -> None:
    por_codigo = {p["codigo"]: p for p in _propriedades(feicoes)}
    assert por_codigo["GF"]["tipo"] == "dependencia"
    assert por_codigo["GF"]["soberano"] == "FR"
    assert por_codigo["FR"]["tipo"] == "pais"


def test_porto_rico_e_dependencia_dos_estados_unidos_com_bandeira_propria(
    feicoes: list[dict[str, Any]], seed: dict[str, Any]
) -> None:
    [p] = [p for p in _propriedades(feicoes) if p["codigo"] == "PR"]
    assert p["tipo"] == "dependencia"
    assert p["soberano"] == "US"
    assert p["titulo"] == "Porto Rico (Estados Unidos)"
    assert p["zoom"] == "PR"
    [d] = [d for d in seed["dependencias"] if d["codigo"] == "PR"]
    assert d["nome_pt"] == "Porto Rico (Estados Unidos)"
    assert d["soberano_codigo"] == "US"
    assert d["codigo_bandeira"] == "PR"
    assert d["identidade_do_soberano"] is False
    assert d["na_lista_itamaraty"] is True


NOMES_DAS_DEPENDENCIAS = {
    "ATC": "Ilhas Ashmore e Cartier (Austrália)",
    "CSI": "Ilhas do Mar de Coral (Austrália)",
    "IOA": "Ilha Christmas e Ilhas Cocos (Austrália)",
    "CLP": "Ilha de Clipperton (França)",
    "UM": "Ilhas Menores Distantes (Estados Unidos)",
    "VI": "Ilhas Virgens Americanas (Estados Unidos)",
    "MF": "São Martim (França)",
    "SX": "São Martim (Países Baixos)",
}


@pytest.mark.parametrize(("codigo", "nome"), NOMES_DAS_DEPENDENCIAS.items())
def test_nomes_em_portugues_das_dependencias(
    feicoes: list[dict[str, Any]], seed: dict[str, Any], codigo: str, nome: str
) -> None:
    [p] = [p for p in _propriedades(feicoes) if p["codigo"] == codigo]
    assert p["titulo"] == nome
    [d] = [d for d in seed["dependencias"] if d["codigo"] == codigo]
    assert d["nome_pt"] == nome


def test_nome_de_dependencia_nao_repete_o_soberano_nem_se_repete(seed: dict[str, Any]) -> None:
    nomes = [d["nome_pt"] for d in seed["dependencias"]]
    assert len(nomes) == len(set(nomes))
    for nome in nomes:
        antes, _, depois = nome.partition(" (")
        assert depois == "" or depois.rstrip(")") not in antes, nome


def test_ilhas_que_dividem_o_codigo_do_pais_viram_dependencia(
    feicoes: list[dict[str, Any]],
) -> None:
    # Clipperton tem código ISO "FR" no Natural Earth, mas é um território à parte
    clipperton = [p for p in _propriedades(feicoes) if "Clipperton" in p["titulo"]]
    assert len(clipperton) == 1
    assert clipperton[0]["tipo"] == "dependencia"
    assert clipperton[0]["soberano"] == "FR"


def test_dependencias_comuns_usam_a_propria_bandeira_e_nome_com_pais(
    seed: dict[str, Any],
) -> None:
    [groenlandia] = [d for d in seed["dependencias"] if d["codigo"] == "GL"]
    assert groenlandia["nome_pt"] == "Groenlândia (Dinamarca)"
    assert groenlandia["soberano_codigo"] == "DK"
    assert groenlandia["codigo_bandeira"] == "GL"
    assert groenlandia["identidade_do_soberano"] is False


def test_dependencias_que_estao_na_lista_do_itamaraty(
    seed: dict[str, Any], itamaraty: set[str]
) -> None:
    na_lista = {d["codigo"] for d in seed["dependencias"] if d["na_lista_itamaraty"]}
    assert na_lista == DEPENDENCIAS_NA_LISTA
    assert na_lista <= itamaraty


def test_kosovo_e_malvinas_usam_nome_e_bandeira_do_soberano(seed: dict[str, Any]) -> None:
    por_codigo = {d["codigo"]: d for d in seed["dependencias"]}
    assert por_codigo["XK"]["nome_pt"] == "Sérvia"
    assert por_codigo["XK"]["codigo_bandeira"] == "RS"
    assert por_codigo["XK"]["identidade_do_soberano"] is True
    assert por_codigo["FK"]["nome_pt"] == "Argentina"
    assert por_codigo["FK"]["codigo_bandeira"] == "AR"
    assert por_codigo["FK"]["identidade_do_soberano"] is True
    # só esses dois têm a identidade do soberano
    com_identidade = [d["codigo"] for d in seed["dependencias"] if d["identidade_do_soberano"]]
    assert sorted(com_identidade) == ["FK", "XK"]


def test_icone_dos_paises_sem_posto(seed: dict[str, Any]) -> None:
    sem_posto = {linha["pais_iso"] for linha in _csv("jurisdicao_cumulativa.csv")}
    com_icone = {i["codigo"] for i in seed["icones_sem_posto"]}
    assert sem_posto == com_icone
    for icone in seed["icones_sem_posto"]:
        assert -90 <= icone["latitude"] <= 90
        assert -180 <= icone["longitude"] <= 180


def test_arquivo_de_geometria_nao_cresce_sem_querer(feicoes: list[dict[str, Any]]) -> None:
    assert GEOJSON.stat().st_size < LIMITE_DE_BYTES
    contagem = Counter(p["tipo"] for p in _propriedades(feicoes))
    # 198 da lista menos Taiwan, Guiana Francesa e Porto Rico, que são dependências
    assert contagem["pais"] == 195
