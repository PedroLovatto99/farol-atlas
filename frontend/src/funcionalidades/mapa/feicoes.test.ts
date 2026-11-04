import { describe, expect, it } from "vitest";
import { NIVEIS, type NivelId } from "../../compartilhado/niveis";
import {
  COR_DA_AREA_NEUTRA,
  COR_DA_BORDA_REGIONAL,
  COR_SEM_PREENCHIMENTO,
  SEM_PREENCHIMENTO,
  preenchimentoDeAlerta,
  preenchimentoDeVisto,
} from "./cor";
import { montarFeicoes, type Geometria } from "./feicoes";
import type { Preenchimento, TerritorioDesenhado } from "./tipos";

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

const desenhado = (codigo: string, nivel: NivelId): TerritorioDesenhado => ({
  codigo,
  preenchimento: preenchimentoDeAlerta("pais", nivel),
  bordaRegional: null,
  esmaecido: false,
});

const comPreenchimento = (
  codigo: string,
  preenchimento: Preenchimento,
  extras: Partial<TerritorioDesenhado> = {},
): TerritorioDesenhado => ({
  codigo,
  preenchimento,
  bordaRegional: null,
  esmaecido: false,
  ...extras,
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

describe("montarFeicoes: esmaecimento do filtro (FR-025)", () => {
  it("marca como esmaecido o que o filtro esmaeceu, mantendo a cor do nível", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      { ...desenhado("BO", "sem_alerta"), esmaecido: true },
      desenhado("LB", "evitar"),
    ]);
    const por = Object.fromEntries(
      resultado.features.map((f) => [f.properties.codigo, f.properties]),
    );
    expect(por["BO"]?.esmaecido).toBe(true);
    expect(por["BO"]?.cor).toBe(NIVEIS.sem_alerta.cor);
    expect(por["LB"]?.esmaecido).toBe(false);
  });

  it("área neutra e território sem informação nunca esmaecem", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      { ...desenhado("BO", "sem_alerta"), esmaecido: true },
    ]);
    const por = Object.fromEntries(
      resultado.features.map((f) => [f.properties.codigo, f.properties]),
    );
    expect(por["AQ"]?.esmaecido).toBe(false);
    expect(por["LB"]?.esmaecido).toBe(false);
  });
});

describe("montarFeicoes: preenchimento e padrão", () => {
  const porCodigo = (resultado: ReturnType<typeof montarFeicoes>) =>
    Object.fromEntries(resultado.features.map((f) => [f.properties.codigo, f.properties]));

  it("leva a cor e o padrão do preenchimento para as propriedades da feição", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      comPreenchimento("BO", preenchimentoDeVisto("pais", "isento", true)),
      comPreenchimento("LB", preenchimentoDeVisto("pais", "visto_exigido", false)),
    ]);
    expect(porCodigo(resultado)["BO"]).toMatchObject({
      cor: "#FEDD50",
      padrao: "rg",
      sem_preenchimento: false,
    });
    expect(porCodigo(resultado)["LB"]).toMatchObject({
      cor: "#3B1C6B",
      padrao: null,
      sem_preenchimento: false,
    });
  });

  it("no modo Alertas nenhuma feição tem padrão nem fica sem preenchimento", () => {
    const resultado = montarFeicoes(GEOMETRIA, [desenhado("BO", "sem_alerta")]);
    for (const f of resultado.features) {
      expect(f.properties.padrao).toBeNull();
      expect(f.properties.sem_preenchimento).toBe(false);
    }
  });

  it("'sem preenchimento' vira a propriedade sem_preenchimento, nunca o cinza de 'sem informação'", () => {
    const resultado = montarFeicoes(GEOMETRIA, [comPreenchimento("BO", SEM_PREENCHIMENTO)]);
    const bo = porCodigo(resultado)["BO"];
    expect(bo?.sem_preenchimento).toBe(true);
    expect(bo?.cor).toBe(COR_SEM_PREENCHIMENTO);
    expect(bo?.cor).not.toBe("#BEBAB1");
  });

  it("no modo Vistos, território ausente da lista fica sem preenchimento (não 'não verificado')", () => {
    const resultado = montarFeicoes(GEOMETRIA, [], "vistos");
    expect(porCodigo(resultado)["BO"]?.sem_preenchimento).toBe(true);
    expect(porCodigo(resultado)["LB"]?.sem_preenchimento).toBe(true);
    expect(porCodigo(resultado)["AQ"]).toMatchObject({ cor: "#F1EFE8", sem_preenchimento: false });
  });

  it("área neutra continua neutra no modo Vistos, mesmo recebendo 'sem preenchimento'", () => {
    const resultado = montarFeicoes(
      GEOMETRIA,
      [comPreenchimento("AQ", SEM_PREENCHIMENTO)],
      "vistos",
    );
    expect(porCodigo(resultado)["AQ"]?.cor).toBe(COR_DA_AREA_NEUTRA);
    expect(porCodigo(resultado)["AQ"]?.sem_preenchimento).toBe(false);
  });

  it("o esmaecido vem do filtro do modo, e nenhuma feição tem borda regional sem ela", () => {
    const resultado = montarFeicoes(
      GEOMETRIA,
      [
        comPreenchimento("BO", preenchimentoDeVisto("pais", "visto_exigido", false), {
          esmaecido: true,
        }),
        comPreenchimento("LB", preenchimentoDeVisto("pais", "isento", false)),
      ],
      "vistos",
    );
    expect(porCodigo(resultado)["BO"]?.esmaecido).toBe(true);
    expect(porCodigo(resultado)["LB"]?.esmaecido).toBe(false);
    for (const f of resultado.features) expect("borda_regional" in f.properties).toBe(false);
  });
});

describe("montarFeicoes com o modo daltonismo", () => {
  const propriedades = (resultado: ReturnType<typeof montarFeicoes>) =>
    Object.fromEntries(resultado.features.map((f) => [f.properties.codigo, f.properties]));
  const comNivel = (codigo: string, nivel: NivelId) =>
    comPreenchimento(codigo, preenchimentoDeAlerta("pais", nivel, true));

  it("grava a imagem de cada padrão, e nada nos territórios sem padrão", () => {
    const resultado = montarFeicoes(
      GEOMETRIA,
      [comNivel("BO", "sem_alerta"), comNivel("LB", "nao_viajar"), comNivel("XK", "evitar")],
      "alertas",
      true,
    );
    const feicoes = propriedades(resultado);
    expect(feicoes["BO"]).not.toHaveProperty("imagem_do_padrao");
    expect(feicoes["LB"]?.imagem_do_padrao).toBe("hachura-nao-viaje");
    expect(feicoes["XK"]?.imagem_do_padrao).toBe("pontos-evite");
    expect(feicoes["AQ"]).not.toHaveProperty("imagem_do_padrao");
  });

  it("o RG usa as listras do modo ligado; desligado, as de hoje", () => {
    const rg = comPreenchimento("BO", preenchimentoDeVisto("pais", "isento", true));
    expect(propriedades(montarFeicoes(GEOMETRIA, [rg], "vistos", true))["BO"]).toMatchObject({
      imagem_do_padrao: "listras-rg-daltonismo",
    });
    expect(propriedades(montarFeicoes(GEOMETRIA, [rg], "vistos"))["BO"]).toMatchObject({
      imagem_do_padrao: "listras-rg",
    });
  });

  it("usa as bordas da paleta, com tracejado só em 'evite'", () => {
    const resultado = montarFeicoes(
      GEOMETRIA,
      [
        comPreenchimento("BO", preenchimentoDeAlerta("pais", "sem_alerta", true), {
          bordaRegional: "nao_viajar",
        }),
        comPreenchimento("LB", preenchimentoDeAlerta("pais", "sem_alerta", true), {
          bordaRegional: "evitar",
        }),
      ],
      "alertas",
      true,
    );
    const feicoes = propriedades(resultado);
    expect(feicoes["BO"]?.borda_regional).toBe("#861212");
    expect(feicoes["BO"]).not.toHaveProperty("borda_tracejada");
    expect(feicoes["LB"]?.borda_regional).toBe("#8C641A");
    expect(feicoes["LB"]?.borda_tracejada).toBe(true);
  });

  it("com o modo desligado, borda_tracejada nunca existe e as cores são as de hoje (FR-015)", () => {
    const resultado = montarFeicoes(GEOMETRIA, [
      comPreenchimento("BO", preenchimentoDeAlerta("pais", "evitar"), { bordaRegional: "evitar" }),
      comPreenchimento("LB", preenchimentoDeAlerta("pais", "nao_viajar"), {
        bordaRegional: "nao_viajar",
      }),
    ]);
    for (const f of resultado.features) {
      expect(f.properties).not.toHaveProperty("borda_tracejada");
      expect(f.properties).not.toHaveProperty("imagem_do_padrao");
    }
    expect(propriedades(resultado)["BO"]?.borda_regional).toBe(COR_DA_BORDA_REGIONAL.evitar);
  });

  it("território sem dado usa o cinza da paleta ativa; área neutra não muda", () => {
    const feicoes = propriedades(montarFeicoes(GEOMETRIA, [], "alertas", true));
    expect(feicoes["BO"]?.cor).toBe("#878C92");
    expect(feicoes["BO"]?.padrao).toBeNull();
    expect(feicoes["AQ"]?.cor).toBe(COR_DA_AREA_NEUTRA);
  });

  it("em 'Vistos', território sem dado continua sem preenchimento", () => {
    const feicoes = propriedades(montarFeicoes(GEOMETRIA, [], "vistos", true));
    expect(feicoes["BO"]?.sem_preenchimento).toBe(true);
  });
});
