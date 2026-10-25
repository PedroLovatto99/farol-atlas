"""Gera a geometria do mapa e o seed de territórios (derivado de prototipos/mapa/montar_dados.py).

Rode só quando as regras de território mudarem. Saídas, versionadas no repositório:

  frontend/public/geo/territorios.geojson   desenho dos territórios (servido pelo frontend)
  dados/territorios/territorios.json        dependências e ícones dos países sem posto (seed)

Entrada: Natural Earth 10m, países, versão "ponto de vista do Brasil", já pré-processada.

  1. Baixar (https://www.naturalearthdata.com/ ou https://naciscdn.org/naturalearth/):
       10m/cultural/ne_10m_admin_0_countries_bra.zip
  2. Pré-processar com o mapshaper (precisão 0.0005, para o Vaticano não sumir). A simplificação de
     20% mantém os postos dentro do desenho do próprio país (a 5% o ícone de Genebra caía na
     França e o de Nassau, no mar); o arquivo final tem 2,1 MB (700 KB comprimido):

       npx mapshaper ne_10m_admin_0_countries_bra.shp \\
         -rename-fields nome=ADMIN,iso=ISO_A2_EH,soberano=SOVEREIGNT,a3=ADM0_A3 \\
         -filter-fields nome,iso,soberano,a3 \\
         -simplify 20% keep-shapes \\
         -o natural_earth_bra.geojson format=geojson precision=0.0005

  3. Gerar:

       uv run --group geo python scripts/gerar_geometria.py \\
         natural_earth_bra.geojson ../dados/postos \\
         ../frontend/public/geo/territorios.geojson ../dados/territorios/territorios.json

Regras de território (spec "Regras do mapa"):
  - Os 198 da lista são os do Itamaraty (CSVs de dados/postos, mais o Brasil): 195 países e três
    entradas desenhadas como dependência (Taiwan, Guiana Francesa e Porto Rico).
  - Kosovo (XK) e Malvinas (FK): dependências com a identidade do soberano (Sérvia e Argentina).
  - Taiwan (TW): dependência da China, sem bandeira.
  - Dependências seguem o soberano; a Guiana Francesa (GF) é separada da França e Porto Rico (PR)
    é dos Estados Unidos, ambos com bandeira própria.
  - Antártida, Saara Ocidental e áreas sem soberania reconhecida são neutras.
"""

import csv
import gettext
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pycountry
from shapely.geometry import MultiPolygon, Point, mapping, shape
from shapely.geometry.base import BaseGeometry

# Áreas neutras: disputas e territórios sem população (o "-99" é o código das sem ISO)
NEUTRO = {"-99", "AQ", "EH", "TF", "GS", "HM", "IO"}

# Kosovo e Malvinas usam o nome, a bandeira e o painel do soberano (spec FR-030 e FR-034)
IDENTIDADE_DO_SOBERANO = {"XK": "RS", "FK": "AR"}

# Taiwan: dependência da China, sem bandeira (FR-033)
TAIWAN = "TW"
CHINA = "CN"

# Entradas da lista do Itamaraty que o mapa desenha como dependência (seguem o soberano):
# a Guiana Francesa (da França) e Porto Rico (dos Estados Unidos). Taiwan tem tratamento próprio.
DEPENDENCIAS_NA_LISTA = {"GF": "FR", "PR": "US"}

# Caixa que recorta a Guiana Francesa do polígono da França
GUIANA_LON = (-55.5, -51.0)
GUIANA_LAT = (1.5, 6.5)

ALIAS_DE_CIDADE = {"cambera": "camberra"}

# Nomes em português que não saem da tradução do ISO 3166 nem do Natural Earth. O soberano vai
# entre parênteses no título, então o nome não o repete (ex.: os dois São Martim se distinguem
# por "(França)" e "(Países Baixos)").
NOMES_PT = {
    "ATC": "Ilhas Ashmore e Cartier",
    "CSI": "Ilhas do Mar de Coral",
    "IOA": "Ilha Christmas e Ilhas Cocos",
    "CLP": "Ilha de Clipperton",
    "UM": "Ilhas Menores Distantes",
    "VI": "Ilhas Virgens Americanas",
    "MF": "São Martim",
    "SX": "São Martim",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


_TRADUCAO = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["pt_BR"])


def _nome_pt_territorio(codigo: str, padrao: str) -> str:
    if codigo in NOMES_PT:
        return NOMES_PT[codigo]
    pais = pycountry.countries.get(alpha_2=codigo)
    if pais is None:
        return padrao
    nome = _TRADUCAO.gettext(getattr(pais, "common_name", pais.name))
    return str(nome).split(",")[0]


def _pedacos(geometria: BaseGeometry) -> list[BaseGeometry]:
    return list(geometria.geoms) if isinstance(geometria, MultiPolygon) else [geometria]


def ler_itamaraty(pasta_postos: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Nomes em português dos 198 países do Itamaraty e as linhas dos países sem posto."""
    nomes = {"BR": "Brasil"}
    with (pasta_postos / "postos_brasileiros.csv").open(encoding="utf-8", newline="") as a:
        postos = list(csv.DictReader(a))
    with (pasta_postos / "jurisdicao_cumulativa.csv").open(encoding="utf-8", newline="") as a:
        sem_posto = list(csv.DictReader(a))
    for linha in postos + sem_posto:
        nomes[linha["pais_iso"]] = linha["pais"]
    return nomes, sem_posto


def _feicao(geometria: dict[str, Any], **propriedades: Any) -> dict[str, Any]:
    return {"type": "Feature", "properties": propriedades, "geometry": geometria}


def _dependencia(
    codigo: str,
    soberano: str,
    titulo: str,
    geometria: dict[str, Any],
    *,
    zoom: str,
    bandeira: str | None,
    identidade: bool = False,
    na_lista: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    feicao = _feicao(
        geometria, codigo=codigo, soberano=soberano, tipo="dependencia", titulo=titulo, zoom=zoom
    )
    seed = {
        "codigo": codigo,
        "nome_pt": titulo,
        "soberano_codigo": soberano,
        "codigo_bandeira": bandeira,
        "identidade_do_soberano": identidade,
        "na_lista_itamaraty": na_lista,
    }
    return feicao, seed


def gerar(
    natural_earth: dict[str, Any],
    nomes_itamaraty: dict[str, str],
    sem_posto: list[dict[str, str]],
    icones_anteriores: dict[str, tuple[float, float]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Devolve (geojson, seed, avisos).

    `icones_anteriores` (código → latitude, longitude) são os ícones do seed atual: um ícone que
    ainda cai dentro do desenho do país é mantido, para que mudar a simplificação não mova o ícone
    (com mais detalhe, a "maior parte" do arquipélago das Seychelles passou a ser Aldabra, a mais
    de mil quilômetros da capital).
    """
    avisos: list[str] = []
    entradas = natural_earth["features"]
    principal = {
        f["properties"]["nome"]: f["properties"]["iso"]
        for f in entradas
        if f["properties"]["nome"] == f["properties"]["soberano"]
    }
    contagem = Counter(f["properties"]["iso"] for f in entradas)

    feicoes: list[dict[str, Any]] = []
    dependencias: list[dict[str, Any]] = []

    for entrada in entradas:
        p = entrada["properties"]
        iso, nome_en, soberano_en, a3 = p["iso"], p["nome"], p["soberano"], p["a3"]
        geometria = entrada["geometry"]

        if iso in IDENTIDADE_DO_SOBERANO:
            soberano = IDENTIDADE_DO_SOBERANO[iso]
            feicao, seed = _dependencia(
                iso, soberano, nomes_itamaraty[soberano], geometria,
                zoom=soberano, bandeira=soberano, identidade=True,
            )  # fmt: skip
            feicoes.append(feicao)
            dependencias.append(seed)
            continue

        if iso == TAIWAN:
            feicao, seed = _dependencia(
                iso, CHINA, "Taiwan (China)", geometria,
                zoom=iso, bandeira=None, na_lista=iso in nomes_itamaraty,
            )  # fmt: skip
            feicoes.append(feicao)
            dependencias.append(seed)
            continue

        # Ilhas que dividem o código ISO com o país (Clipperton/FR, ilhas australianas/AU)
        if iso in nomes_itamaraty and contagem[iso] > 1 and nome_en != soberano_en:
            titulo = f"{_nome_pt_territorio(a3, nome_en)} ({nomes_itamaraty[iso]})"
            feicao, seed = _dependencia(
                a3, iso, titulo, geometria, zoom=a3, bandeira=iso,
            )  # fmt: skip
            feicoes.append(feicao)
            dependencias.append(seed)
            continue

        partes: list[tuple[str, dict[str, Any]]] = [(iso, geometria)]
        if iso == "FR" and nome_en == "France":
            pedacos = _pedacos(shape(geometria))
            guiana = [
                g
                for g in pedacos
                if GUIANA_LON[0] < g.centroid.x < GUIANA_LON[1]
                and GUIANA_LAT[0] < g.centroid.y < GUIANA_LAT[1]
            ]
            resto = [g for g in pedacos if g not in guiana]
            partes = [("FR", mapping(MultiPolygon(resto))), ("GF", mapping(MultiPolygon(guiana)))]

        for codigo, geom in partes:
            if codigo in DEPENDENCIAS_NA_LISTA:
                da_lista = DEPENDENCIAS_NA_LISTA[codigo]
                titulo = f"{nomes_itamaraty[codigo]} ({nomes_itamaraty[da_lista]})"
                feicao, seed = _dependencia(
                    codigo, da_lista, titulo, geom,
                    zoom=codigo, bandeira=codigo, na_lista=codigo in nomes_itamaraty,
                )  # fmt: skip
                feicoes.append(feicao)
                dependencias.append(seed)
            elif codigo in NEUTRO:
                titulo = _nome_pt_territorio(codigo, nome_en)
                feicoes.append(
                    _feicao(
                        geom, codigo=codigo, soberano=None, tipo="neutro", titulo=titulo, zoom=None
                    )
                )
            elif codigo in nomes_itamaraty:
                feicoes.append(
                    _feicao(
                        geom,
                        codigo=codigo,
                        soberano=None,
                        tipo="pais",
                        titulo=nomes_itamaraty[codigo],
                        zoom=codigo,
                    )
                )
            else:
                pai = principal.get(soberano_en)
                if pai in nomes_itamaraty:
                    titulo = f"{_nome_pt_territorio(codigo, nome_en)} ({nomes_itamaraty[pai]})"
                    feicao, seed = _dependencia(
                        codigo, pai, titulo, geom, zoom=codigo, bandeira=codigo
                    )
                    feicoes.append(feicao)
                    dependencias.append(seed)
                else:
                    titulo = _nome_pt_territorio(codigo, nome_en)
                    feicoes.append(
                        _feicao(
                            geom,
                            codigo=codigo,
                            soberano=None,
                            tipo="neutro",
                            titulo=titulo,
                            zoom=None,
                        )
                    )

    # Taiwan e Guiana Francesa estão na lista do Itamaraty, mas são desenhados como dependências
    desenhados = {
        f["properties"]["codigo"]
        for f in feicoes
        if f["properties"]["tipo"] in {"pais", "dependencia"}
    }
    faltando = sorted(set(nomes_itamaraty) - desenhados)
    if faltando:
        avisos.append(f"países do Itamaraty sem desenho: {faltando}")

    # Ícone do país sem posto: um ponto dentro da maior parte do território
    icones: list[dict[str, Any]] = []
    for linha in sem_posto:
        iso = linha["pais_iso"]
        do_pais = [f for f in feicoes if f["properties"]["codigo"] == iso]
        if not do_pais:
            avisos.append(f"sem desenho para {iso}")
            continue
        pedacos = [g for f in do_pais for g in _pedacos(shape(f["geometry"]))]
        anterior = (icones_anteriores or {}).get(iso)
        if anterior is not None and any(p.covers(Point(anterior[1], anterior[0])) for p in pedacos):
            icones.append({"codigo": iso, "latitude": anterior[0], "longitude": anterior[1]})
            continue
        ponto = max(pedacos, key=lambda g: g.area).representative_point()
        icones.append(
            {"codigo": iso, "latitude": round(ponto.y, 5), "longitude": round(ponto.x, 5)}
        )

    geojson = {"type": "FeatureCollection", "features": feicoes}
    seed = {
        "dependencias": sorted(dependencias, key=lambda d: d["codigo"]),
        "icones_sem_posto": sorted(icones, key=lambda i: i["codigo"]),
    }
    return geojson, seed, avisos


def _icones_do_seed(caminho: Path) -> dict[str, tuple[float, float]]:
    if not caminho.exists():
        return {}
    seed = json.loads(caminho.read_text(encoding="utf-8"))
    return {i["codigo"]: (i["latitude"], i["longitude"]) for i in seed["icones_sem_posto"]}


def main(argumentos: list[str]) -> int:
    if len(argumentos) != 4:
        print(__doc__)
        print(
            "uso: gerar_geometria.py <natural_earth.geojson> <pasta_postos> "
            "<saida.geojson> <saida_seed.json>"
        )
        return 2
    entrada, pasta_postos, saida_geojson, saida_seed = (Path(a) for a in argumentos)
    natural_earth = json.loads(entrada.read_text(encoding="utf-8"))
    nomes, sem_posto = ler_itamaraty(pasta_postos)
    geojson, seed, avisos = gerar(natural_earth, nomes, sem_posto, _icones_do_seed(saida_seed))
    for aviso in avisos:
        print("AVISO:", aviso)
    saida_geojson.parent.mkdir(parents=True, exist_ok=True)
    saida_seed.parent.mkdir(parents=True, exist_ok=True)
    saida_geojson.write_text(
        json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    saida_seed.write_text(
        json.dumps(seed, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    tipos = Counter(f["properties"]["tipo"] for f in geojson["features"])
    print(f"feições: {dict(tipos)} | {saida_geojson.stat().st_size / 1024:.0f} KB")
    print(
        f"dependências no seed: {len(seed['dependencias'])} | "
        f"ícones sem posto: {len(seed['icones_sem_posto'])}"
    )
    return 1 if avisos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
