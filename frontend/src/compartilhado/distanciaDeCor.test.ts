import { describe, expect, it } from "vitest";
import { rgbDeHex } from "./contraste";
import {
  distanciaCiede2000,
  distanciaEntreCores,
  labDeRgb,
  simularDaltonismo,
  type TipoDeDaltonismo,
} from "./distanciaDeCor";

type Lab = readonly [number, number, number];

describe("CIEDE2000", () => {
  // Pares do conjunto de referência de Sharma, Wu e Dalal (2005), com 4 casas decimais
  it.each<[Lab, Lab, number]>([
    [[50, 2.6772, -79.7751], [50, 0, -82.7485], 2.0425],
    [[50, 3.1571, -77.2803], [50, 0, -82.7485], 2.8615],
    [[50, 2.5, 0], [50, 0, -2.5], 4.3065],
    [[50, 0, 0], [50, -1, 2], 2.3669],
    [[60.2574, -34.0099, 36.2677], [60.4626, -34.1751, 39.4387], 1.2644],
  ])("%j × %j = %f", (a, b, esperado) => {
    expect(distanciaCiede2000(a, b)).toBeCloseTo(esperado, 3);
  });

  it("é simétrica", () => {
    const a: Lab = [50, 2.6772, -79.7751];
    const b: Lab = [60, 20, 10];
    expect(distanciaCiede2000(a, b)).toBeCloseTo(distanciaCiede2000(b, a), 9);
  });

  it("a distância de uma cor para ela mesma é 0", () => {
    expect(distanciaCiede2000([50, 10, -20], [50, 10, -20])).toBe(0);
    expect(distanciaEntreCores(rgbDeHex("#FEDD50"), rgbDeHex("#FEDD50"))).toBe(0);
  });
});

describe("conversão para Lab", () => {
  it("branco é L 100 e preto é L 0", () => {
    const [lb, ab, bb] = labDeRgb([255, 255, 255]);
    expect(lb).toBeCloseTo(100, 1);
    expect(Math.abs(ab)).toBeLessThan(0.01);
    expect(Math.abs(bb)).toBeLessThan(0.01);
    expect(labDeRgb([0, 0, 0])[0]).toBeCloseTo(0, 3);
  });

  it("vermelho puro tem o Lab conhecido (53,2; 80,1; 67,2)", () => {
    const [l, a, b] = labDeRgb([255, 0, 0]);
    expect(l).toBeCloseTo(53.24, 1);
    expect(a).toBeCloseTo(80.09, 1);
    expect(b).toBeCloseTo(67.2, 1);
  });
});

describe("simulação de daltonismo", () => {
  const TIPOS: TipoDeDaltonismo[] = ["protanopia", "deuteranopia", "tritanopia"];

  it.each(TIPOS)("%s: cinzas continuam cinzas (a matriz soma 1 por linha)", (tipo) => {
    for (const nivel of [0, 64, 128, 200, 255]) {
      const [r, g, b] = simularDaltonismo([nivel, nivel, nivel], tipo);
      expect(Math.abs(r - nivel)).toBeLessThanOrEqual(1);
      expect(Math.abs(g - nivel)).toBeLessThanOrEqual(1);
      expect(Math.abs(b - nivel)).toBeLessThanOrEqual(1);
    }
  });

  it("protanopia e deuteranopia aproximam o vermelho do verde", () => {
    const vermelho = rgbDeHex("#E24B4A");
    const verde = rgbDeHex("#C0DD97");
    const normal = distanciaEntreCores(vermelho, verde);
    for (const tipo of ["protanopia", "deuteranopia"] as const) {
      const simulado = distanciaEntreCores(
        simularDaltonismo(vermelho, tipo),
        simularDaltonismo(verde, tipo),
      );
      expect(simulado).toBeLessThan(normal);
    }
  });

  it("devolve canais inteiros entre 0 e 255", () => {
    for (const tipo of TIPOS) {
      for (const canal of simularDaltonismo([12, 200, 255], tipo)) {
        expect(Number.isInteger(canal)).toBe(true);
        expect(canal).toBeGreaterThanOrEqual(0);
        expect(canal).toBeLessThanOrEqual(255);
      }
    }
  });
});
