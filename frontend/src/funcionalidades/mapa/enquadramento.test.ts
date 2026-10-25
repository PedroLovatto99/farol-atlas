import { describe, expect, it } from "vitest";
import {
  LIMITE_DE_LARGURA,
  ZOOM_MAXIMO,
  calcularEnquadramento,
  duracaoDoMovimento,
  margemDoLayout,
} from "./enquadramento";
import type { Geometria } from "./feicoes";
import type { Margem } from "./tipos";

const MARGEM: Margem = { topo: 60, esquerda: 20, direita: 380, baixo: 20 };

function retangulo(oeste: number, sul: number, leste: number, norte: number) {
  return [
    [
      [oeste, sul],
      [leste, sul],
      [leste, norte],
      [oeste, norte],
      [oeste, sul],
    ],
  ];
}

function feicao(
  codigo: string,
  zoom: string | null,
  geometry: unknown,
  tipo: "pais" | "dependencia" | "neutro" = "pais",
) {
  return {
    type: "Feature" as const,
    properties: { codigo, tipo, soberano: null, titulo: codigo, zoom },
    geometry,
  };
}

const GEOMETRIA: Geometria = {
  type: "FeatureCollection",
  features: [
    // França: a parte continental é a maior; o ultramar fica longe e não conta
    feicao("FR", "FR", {
      type: "MultiPolygon",
      coordinates: [
        retangulo(-55, 2, -51, 6), // Guiana, pequena
        retangulo(-5, 42, 8, 51), // continental, a maior
        retangulo(55, -21.5, 56, -20.8), // Reunião, pequena
      ],
    }),
    // Rússia cruza a antimeridiana: a Chukotka aparece em longitudes negativas
    feicao("RU", "RU", {
      type: "MultiPolygon",
      coordinates: [retangulo(27, 41, 180, 77), retangulo(-180, 64, -169, 69)],
    }),
    feicao("DK", "DK", { type: "Polygon", coordinates: retangulo(8, 54.5, 15, 57.8) }),
    // Kosovo e Malvinas usam o grupo do soberano
    feicao("RS", "RS", { type: "Polygon", coordinates: retangulo(18.8, 42.2, 23, 46.2) }),
    feicao(
      "XK",
      "RS",
      { type: "Polygon", coordinates: retangulo(20, 42.3, 21.8, 43.3) },
      "dependencia",
    ),
    feicao("TO", "TO", { type: "Polygon", coordinates: retangulo(-175.5, -21.5, -173.5, -18.5) }),
    feicao("EH", null, { type: "Polygon", coordinates: retangulo(-17, 20, -8.7, 27.7) }, "neutro"),
  ],
};

function enquadrar(codigo: string, responsavel: { latitude: number; longitude: number } | null) {
  const pedido = calcularEnquadramento({
    geometria: GEOMETRIA,
    codigo,
    responsavel,
    margem: MARGEM,
  });
  if (pedido === null || pedido.tipo !== "enquadrar") {
    throw new Error(`sem enquadramento para ${codigo}`);
  }
  return pedido;
}

describe("calcularEnquadramento", () => {
  it("usa a maior parte do território: a França não mostra o mundo", () => {
    expect(enquadrar("FR", null).caixa).toEqual([
      [-5, 42],
      [8, 51],
    ]);
  });

  it("usa a maior parte da Rússia, sem a Chukotka do outro lado da antimeridiana", () => {
    const [[oeste], [leste]] = enquadrar("RU", null).caixa;
    expect(oeste).toBe(27);
    expect(leste).toBe(180);
  });

  it("passa a margem e o zoom máximo de 5,5", () => {
    const pedido = enquadrar("DK", null);
    expect(pedido.margem).toEqual(MARGEM);
    expect(pedido.zoomMaximo).toBe(5.5);
    expect(ZOOM_MAXIMO).toBe(5.5);
  });

  it("Kosovo enquadra o grupo da Sérvia", () => {
    const daSerbia = enquadrar("RS", null).caixa;
    expect(enquadrar("XK", null).caixa).toEqual(daSerbia);
    expect(daSerbia).toEqual([
      [18.8, 42.2],
      [23, 46.2],
    ]);
  });

  it("inclui o posto responsável quando a largura fica abaixo de 180°", () => {
    // Dinamarca (8 a 15) e Londres (-0,12): pouco mais de 15° de largura
    const pedido = enquadrar("DK", { latitude: 51.5, longitude: -0.12 });
    expect(pedido.caixa).toEqual([
      [-0.12, 51.5],
      [15, 57.8],
    ]);
  });

  it("não inclui o posto responsável se a largura chegar a 180° ou mais", () => {
    // Tonga (-175,5) e um responsável em Auckland (174,8): juntar daria a volta ao mundo
    const so = enquadrar("TO", null).caixa;
    expect(enquadrar("TO", { latitude: -36.85, longitude: 174.76 }).caixa).toEqual(so);
  });

  it("no limite exato de 180° não inclui o responsável", () => {
    expect(LIMITE_DE_LARGURA).toBe(180);
    const so = enquadrar("DK", null).caixa; // oeste 8
    expect(enquadrar("DK", { latitude: 0, longitude: 188 }).caixa).toEqual(so); // 188 - 8 = 180
  });

  it("devolve nulo para código sem geometria e para área neutra sem grupo", () => {
    const entrada = { geometria: GEOMETRIA, responsavel: null, margem: MARGEM };
    expect(calcularEnquadramento({ ...entrada, codigo: "ZZ" })).toBeNull();
    expect(calcularEnquadramento({ ...entrada, codigo: "EH" })).toBeNull();
  });
});

describe("margemDoLayout", () => {
  it("no computador o painel fica à direita", () => {
    expect(margemDoLayout(false, 900)).toEqual({ topo: 60, esquerda: 20, direita: 380, baixo: 20 });
  });

  it("no celular a gaveta ocupa 55% da altura, embaixo", () => {
    expect(margemDoLayout(true, 800)).toEqual({ topo: 60, esquerda: 20, direita: 20, baixo: 440 });
  });
});

describe("duracaoDoMovimento", () => {
  it("é zero com movimento reduzido (FR-039)", () => {
    expect(duracaoDoMovimento(true)).toBe(0);
  });

  it("anima por mais de zero sem a preferência", () => {
    expect(duracaoDoMovimento(false)).toBeGreaterThan(0);
  });
});
