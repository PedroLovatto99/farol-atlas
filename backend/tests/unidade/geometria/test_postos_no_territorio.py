"""Os postos têm de cair no desenho do país a que pertencem (ou muito perto da borda).

Testam os arquivos versionados: a geometria do frontend e os postos do seed. Se alguém regerar a
geometria com simplificação demais, o ícone de um posto sai do contorno do país (foi o caso de
Genebra, que caía na França, e de Nassau, 57 km mar adentro) e este teste falha.
"""

import csv
import json
import math
from pathlib import Path
from typing import Any

import pytest
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, unary_union

RAIZ = Path(__file__).resolve().parents[4]
GEOJSON = RAIZ / "frontend" / "public" / "geo" / "territorios.geojson"
POSTOS = RAIZ / "dados" / "postos" / "postos_brasileiros.csv"

# O ponto é o centro da cidade, que muitas vezes fica na orla ou num rio de fronteira (Cobija,
# Letícia, Montevidéu): mesmo o Natural Earth 10m sem simplificar deixa alguns a poucos km.
TOLERANCIA_EM_KM = 5.0

# Postos que ficam fora do território do país por natureza, com o motivo (id do posto)
EXCECOES = {
    177: "a embaixada junto à Santa Sé fica em Roma, na Itália; o Vaticano mal aparece no mapa",
}


def _distancia_em_km(a: Point, b: Point) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a.y, a.x, b.y, b.x))
    h = (
        math.sin((la2 - la1) / 2) ** 2
        + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    )
    return 2 * 6371 * math.asin(math.sqrt(h))


@pytest.fixture(scope="module")
def territorios() -> dict[str, BaseGeometry]:
    """Desenho de cada país, com as dependências dele (Hong Kong é parte da China, no mapa)."""
    feicoes: list[dict[str, Any]] = json.loads(GEOJSON.read_text(encoding="utf-8"))["features"]
    partes: dict[str, list[BaseGeometry]] = {}
    for feicao in feicoes:
        propriedades = feicao["properties"]
        for codigo in {propriedades["codigo"], propriedades["soberano"]} - {None}:
            partes.setdefault(codigo, []).append(shape(feicao["geometry"]))
    return {codigo: unary_union(geometrias) for codigo, geometrias in partes.items()}


@pytest.fixture(scope="module")
def postos() -> list[dict[str, str]]:
    with POSTOS.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def _ponto(posto: dict[str, str]) -> Point:
    return Point(float(posto["longitude"]), float(posto["latitude"]))


def _distancia_do_posto_ao_pais(
    posto: dict[str, str], territorios: dict[str, BaseGeometry]
) -> float:
    ponto = _ponto(posto)
    desenho = territorios[posto["pais_iso"]]
    if desenho.covers(ponto):
        return 0.0
    _, mais_proximo = nearest_points(ponto, desenho)
    return _distancia_em_km(ponto, mais_proximo)


def test_todo_posto_fica_a_menos_de_5_km_do_desenho_do_proprio_pais(
    postos: list[dict[str, str]], territorios: dict[str, BaseGeometry]
) -> None:
    longe = [
        f"{p['cidade']} ({p['pais_iso']}, id {p['id']}): {d:.1f} km"
        for p in postos
        if int(p["id"]) not in EXCECOES
        and (d := _distancia_do_posto_ao_pais(p, territorios)) > TOLERANCIA_EM_KM
    ]
    assert longe == []


def test_genebra_fica_dentro_da_suica(territorios: dict[str, BaseGeometry]) -> None:
    genebra = Point(6.1469, 46.2017)
    assert territorios["CH"].covers(genebra)
    assert not territorios["FR"].covers(genebra)


def test_toda_excecao_declarada_ainda_e_necessaria(
    postos: list[dict[str, str]], territorios: dict[str, BaseGeometry]
) -> None:
    """Exceção que já cabe no desenho é lixo: tira-se da lista."""
    por_id = {int(p["id"]): p for p in postos}
    assert set(EXCECOES) <= set(por_id)
    for posto_id in EXCECOES:
        assert _distancia_do_posto_ao_pais(por_id[posto_id], territorios) > TOLERANCIA_EM_KM / 10
