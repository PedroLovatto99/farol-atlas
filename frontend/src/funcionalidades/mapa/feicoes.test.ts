import { describe, expect, it } from "vitest";
import { NIVEIS } from "../../compartilhado/niveis";
import { COR_DA_AREA_NEUTRA, COR_DA_BORDA_REGIONAL } from "./cor";
import { montarFeicoes, type Geometria } from "./feicoes";
import type { TerritorioDesenhado } from "./tipos";

function feicao(codigo: string, tipo: "pais" | "dependencia" | "neutro", zoom: string | null) {
  return {
    type: "Feature" as const,
    properties: { codigo, tipo, soberano: null, titulo: codigo, zoom },
    geometry: { type: "Polygon", coordinates: [] },
  };
}

const GEOMETRIA: Geometria = {
  type: "FeatureCollection",
  features: [
    feicao("BO", "pais", "BO"),
    feicao("LB", "pais", "LB"),
    feicao("XK", "dependencia", "RS"),
    feicao("AQ", "neutro", null),
  ],
};

const desenhado = (codigo: string, nivel: TerritorioDesenhado["nivel"]): TerritorioDesenhado => ({
  codigo,
  nivel,
  bordaRegional: null,
  esmaecido: false,
});

describe("montarFeicoes", () => {
  it("pinta cada território com a cor do seu nível", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      desenhado("BO", "sem_alerta"),
      desenhado("LB", "evitar"),
      desenhado("XK", "nao_viajar"),
    ]);
    const cores = Object.fromEntries(
      resultado.features.map((f) => [f.properties.codigo, f.properties.cor]),
    );
    expect(cores["BO"]).toBe(NIVEIS.sem_alerta.cor);
    expect(cores["LB"]).toBe(NIVEIS.evitar.cor);
    expect(cores["XK"]).toBe(NIVEIS.nao_viajar.cor);
  });

  it("território sem informação do backend fica 'não verificado', nunca 'sem alerta'", () => {
    const resultado = montarFeicoes(GEOMETRIA, [desenhado("BO", "sem_alerta")]);
    const lb = resultado.features.find((f) => f.properties.codigo === "LB");
    expect(lb?.properties.cor).toBe(NIVEIS.nao_verificado.cor);
  });

  it("área neutra é sempre neutra", () => {
    const resultado = montarFeicoes(GEOMETRIA, [desenhado("AQ", "nao_viajar")]);
    const aq = resultado.features.find((f) => f.properties.codigo === "AQ");
    expect(aq?.properties.cor).toBe(COR_DA_AREA_NEUTRA);
  });

  it("a borda regional só existe nos territórios que a têm", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      { ...desenhado("LB", "evitar"), bordaRegional: "nao_viajar" },
      desenhado("BO", "sem_alerta"),
    ]);
    const por = Object.fromEntries(
      resultado.features.map((f) => [f.properties.codigo, f.properties]),
    );
    expect(por["LB"]?.borda_regional).toBe(COR_DA_BORDA_REGIONAL.nao_viajar);
    expect(por["BO"] && "borda_regional" in por["BO"]).toBe(false);
  });

  it("mantém os dados originais da feição e não altera a geometria de entrada", () => {
    const antes = JSON.stringify(GEOMETRIA);
    const resultado = montarFeicoes(GEOMETRIA, [desenhado("XK", "evitar")]);
    expect(JSON.stringify(GEOMETRIA)).toBe(antes);
    const xk = resultado.features.find((f) => f.properties.codigo === "XK");
    expect(xk?.properties.zoom).toBe("RS");
    expect(xk?.properties.tipo).toBe("dependencia");
    expect(xk?.geometry).toBe(GEOMETRIA.features[2]?.geometry);
  });
});
