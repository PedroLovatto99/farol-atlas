"""Monta os dados do mapa de teste a partir do Natural Earth (visão BRA) e dos CSVs do Itamaraty."""
import csv
import gettext
import json
import sys
import unicodedata

import pycountry
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

GEOJSON, POSTOS_DIR, SAIDA = sys.argv[1], sys.argv[2], sys.argv[3]

norm = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
pt_tr = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["pt_BR"])

# ---------------------------------------------------------------- Itamaraty
postos = list(csv.DictReader(open(f"{POSTOS_DIR}/postos_brasileiros.csv", encoding="utf-8")))
jurisd = list(csv.DictReader(open(f"{POSTOS_DIR}/jurisdicao_cumulativa.csv", encoding="utf-8")))
NOME_PT = {"BR": "Brasil"}
for r in postos + jurisd:
    NOME_PT[r["pais_iso"]] = r["pais"]
ITA = set(NOME_PT)

# ---------------------------------------------------------------- Regras do mapa
NEUTRO = {"-99", "AQ", "EH", "FK", "GS", "TF", "HM", "IO"}  # disputas e areas sem populacao


def nome_pt_territorio(iso, padrao):
    c = pycountry.countries.get(alpha_2=iso)
    if not c:
        return padrao
    n = pt_tr.gettext(getattr(c, "common_name", c.name))
    return n.split(",")[0]


ne = json.load(open(GEOJSON, encoding="utf-8"))
principal = {f["properties"]["nome"]: f["properties"]["iso"] for f in ne["features"]
             if f["properties"]["nome"] == f["properties"]["soberano"]}


def pedacos(geom):
    g = shape(geom)
    return list(g.geoms) if isinstance(g, MultiPolygon) else [g]


from collections import Counter
contagem = Counter(f["properties"]["iso"] for f in ne["features"])

saida = []
for f in ne["features"]:
    p = f["properties"]
    iso, nome_en, sob = p["iso"], p["nome"], p["soberano"]
    geoms = [(iso, f["geometry"])]

    # Ilhas que dividem o codigo com o pais (Clipperton/FR, ilhas australianas/AU): territorio a parte
    if iso in ITA and contagem[iso] > 1 and nome_en != sob:
        saida.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "tipo": "dependencia", "iso_mapa": iso, "zoom": f"{iso}:{nome_en}", "iso_original": iso,
            "titulo": f"{nome_en} ({NOME_PT[iso]})"}})
        continue

    # Guiana Francesa: separar da Franca pelo recorte geografico
    if iso == "FR" and nome_en == "France":
        partes = pedacos(f["geometry"])
        gf = [g for g in partes if -55.5 < g.centroid.x < -51 and 1.5 < g.centroid.y < 6.5]
        resto = [g for g in partes if g not in gf]
        geoms = [("FR", mapping(MultiPolygon(resto))), ("GF", mapping(MultiPolygon(gf)))]

    for codigo, geom in geoms:
        if codigo == "XK":
            props = {"tipo": "pais", "iso_mapa": "RS", "titulo": NOME_PT["RS"], "zoom": "RS", "obs": "Kosovo: o Brasil não reconhece a independência."}
        elif codigo in NEUTRO:
            props = {"tipo": "neutro", "titulo": nome_pt_territorio(codigo, nome_en)}
        elif codigo in ITA:
            props = {"tipo": "pais", "iso_mapa": codigo, "titulo": NOME_PT[codigo], "zoom": codigo}
        else:
            pai = principal.get(sob)
            if pai in ITA:
                props = {"tipo": "dependencia", "iso_mapa": pai, "zoom": codigo,
                         "titulo": f"{nome_pt_territorio(codigo, nome_en)} ({NOME_PT[pai]})"}
            else:
                props = {"tipo": "neutro", "titulo": nome_pt_territorio(codigo, nome_en)}
        props["iso_original"] = codigo
        saida.append({"type": "Feature", "properties": props, "geometry": geom})

faltando = ITA - {f["properties"].get("iso_mapa") for f in saida}
print("feicoes:", len(saida), "| paises do Itamaraty sem desenho:", sorted(faltando))
print("neutras:", sorted({f["properties"]["iso_original"] for f in saida if f["properties"]["tipo"] == "neutro"}))
print("dependencias:", len([f for f in saida if f["properties"]["tipo"] == "dependencia"]))

# ---------------------------------------------------------------- Marcadores dos postos (agrupados por coordenada)
grupos = {}
for r in postos:
    chave = (r["latitude"], r["longitude"])
    g = grupos.setdefault(chave, {"lat": float(r["latitude"]), "lon": float(r["longitude"]), "cidade": r["cidade"], "postos": []})
    g["postos"].append({"tipo": r["tipo"], "pais_iso": r["pais_iso"], "pais": r["pais"]})
marcadores = list(grupos.values())

# ---------------------------------------------------------------- Paises sem posto: ponto dentro do territorio e posto responsavel
cidade_para_grupo = {}
for g in marcadores:
    cidade_para_grupo.setdefault(norm(g["cidade"]), []).append(g)
ALIAS = {"cambera": "camberra"}

sem_posto = []
for r in jurisd:
    iso = r["pais_iso"]
    feats = [f for f in saida if f["properties"].get("iso_original") == iso]
    if not feats:
        print("sem desenho para", iso)
        continue
    maior = max((g for f in feats for g in pedacos(f["geometry"])), key=lambda g: g.area)
    ponto = maior.representative_point()
    item = {"pais_iso": iso, "pais": r["pais"], "lat": round(ponto.y, 3), "lon": round(ponto.x, 3), "responsavel": None}
    resp = r["posto_responsavel"]
    if not resp.startswith("("):
        cands = cidade_para_grupo.get(ALIAS.get(norm(resp), norm(resp)), [])
        cands = sorted(cands, key=lambda g: any(p["pais_iso"] == "VA" for p in g["postos"]))
        if cands:
            g = cands[0]
            item["responsavel"] = {"cidade": g["cidade"], "lat": g["lat"], "lon": g["lon"],
                                   "tipo": g["postos"][0]["tipo"], "pais": g["postos"][0]["pais"]}
        else:
            print("posto responsavel nao encontrado:", iso, resp)
    sem_posto.append(item)
print("paises sem posto:", len(sem_posto), "| sem responsavel:", [s["pais"] for s in sem_posto if not s["responsavel"]])

# ---------------------------------------------------------------- Alertas de EXEMPLO
alertas = {}   # sem dado = "ainda nao verificado" (cinza)
for iso in ["IR", "IL", "YE"]:
    alertas[iso] = {"nivel": "nao_viajar"}
for iso in ["PS", "LB", "SY", "IQ", "JO", "QA", "KW", "AE", "BH", "SA", "UA"]:
    alertas[iso] = {"nivel": "evitar"}
alertas["LB"]["regioes"] = [{"regiao": "Sul do Líbano", "nivel": "nao_viajar"}]
alertas["PS"]["regioes"] = [{"regiao": "Faixa de Gaza", "nivel": "nao_viajar"}]

dados = {"paises": {"type": "FeatureCollection", "features": saida}, "marcadores": marcadores,
         "sem_posto": sem_posto, "alertas": alertas}
json.dump(dados, open(SAIDA, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("dados.json:", round(len(open(SAIDA, encoding="utf-8").read()) / 1024), "KB")
