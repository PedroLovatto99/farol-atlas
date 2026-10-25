import { describe, expect, it } from "vitest";
import { distanciaAngular, planejarCamera, pontoVisivel, type ContextoDaCamera } from "./camera";
import type { Margem, PedidoDeCamera } from "./tipos";

const MARGEM: Margem = { topo: 60, esquerda: 20, direita: 380, baixo: 20 };
const TAMANHO = { largura: 1280, altura: 800 };
const CENTRO = { longitude: 10, latitude: 50 };

function contexto(sobrescritas: Partial<ContextoDaCamera> = {}): ContextoDaCamera {
  return { centro: CENTRO, pontoNaTela: { x: 400, y: 400 }, tamanho: TAMANHO, ...sobrescritas };
}

const GARANTIR: PedidoDeCamera = {
  tipo: "garantir-visivel",
  latitude: 48,
  longitude: 11,
  margem: MARGEM,
};

describe("distanciaAngular", () => {
  it("é zero no mesmo ponto e 180° em pontos opostos", () => {
    expect(distanciaAngular(CENTRO, CENTRO)).toBeCloseTo(0);
    expect(
      distanciaAngular({ longitude: 0, latitude: 0 }, { longitude: 180, latitude: 0 }),
    ).toBeCloseTo(180);
  });

  it("vale 90° entre a linha do equador e o polo", () => {
    expect(
      distanciaAngular({ longitude: 0, latitude: 0 }, { longitude: 0, latitude: 90 }),
    ).toBeCloseTo(90);
  });
});

describe("pontoVisivel", () => {
  it("está visível dentro da área livre (fora da margem do painel)", () => {
    expect(pontoVisivel(contexto(), { latitude: 48, longitude: 11 }, MARGEM)).toBe(true);
  });

  it.each([
    ["debaixo do painel, à direita", { x: 1000, y: 400 }],
    ["acima da margem do topo", { x: 400, y: 30 }],
    ["abaixo da margem de baixo", { x: 400, y: 790 }],
    ["à esquerda da margem", { x: 5, y: 400 }],
  ])("não está visível %s", (_nome, pontoNaTela) => {
    expect(pontoVisivel(contexto({ pontoNaTela }), { latitude: 48, longitude: 11 }, MARGEM)).toBe(
      false,
    );
  });

  it("não está visível se não tem posição na tela", () => {
    expect(
      pontoVisivel(contexto({ pontoNaTela: null }), { latitude: 48, longitude: 11 }, MARGEM),
    ).toBe(false);
  });

  it("ícone do outro lado do globo nunca está visível, mesmo que a posição caia na tela", () => {
    const outroLado = { latitude: -50, longitude: -170 }; // oposto ao centro (10, 50)
    expect(pontoVisivel(contexto({ pontoNaTela: { x: 400, y: 400 } }), outroLado, MARGEM)).toBe(
      false,
    );
  });
});

describe("planejarCamera", () => {
  it("garantir-visivel não faz nada se o ponto já está na área visível", () => {
    expect(planejarCamera(GARANTIR, () => contexto())).toEqual({ tipo: "nenhum" });
  });

  it("garantir-visivel só desloca o centro quando o ponto está fora, e nunca mexe no zoom", () => {
    const plano = planejarCamera(GARANTIR, () => contexto({ pontoNaTela: { x: 1100, y: 400 } }));
    expect(plano).toEqual({ tipo: "centralizar", latitude: 48, longitude: 11, margem: MARGEM });
    expect(plano).not.toHaveProperty("zoom");
    expect(plano).not.toHaveProperty("zoomMaximo");
  });

  it("manter não reenquadra nem consulta o mapa", () => {
    let consultas = 0;
    const plano = planejarCamera({ tipo: "manter" }, () => {
      consultas += 1;
      return contexto();
    });
    expect(plano).toEqual({ tipo: "nenhum" });
    expect(consultas).toBe(0);
  });

  it("mundo e enquadrar passam como estão", () => {
    const enquadrar: PedidoDeCamera = {
      tipo: "enquadrar",
      caixa: [
        [8, 54],
        [15, 57],
      ],
      margem: MARGEM,
      zoomMaximo: 5.5,
    };
    expect(planejarCamera({ tipo: "mundo" }, () => contexto())).toEqual({ tipo: "mundo" });
    expect(planejarCamera(enquadrar, () => contexto())).toEqual(enquadrar);
  });
});
