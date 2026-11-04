import { describe, expect, it } from "vitest";
import { contraste, rgbDeHex } from "../../compartilhado/contraste";
import {
  COR_DO_BRASIL_NO_MODO_VISTOS,
  COR_DO_CONTORNO_NO_MODO_VISTOS,
  COR_DO_OCEANO,
  CORES_DE_VISTO,
} from "../../compartilhado/vistos";
import { CONTORNO_DO_MODO_VISTOS, contornoDosPaises, transicaoDoContorno } from "./contorno";
import { paletaDe } from "./cor";

describe("contornoDosPaises", () => {
  it("o modo Alertas não muda: linha branca de 0,6 px", () => {
    expect(contornoDosPaises("alertas")).toEqual({ cor: "#ffffff", largura: 0.6 });
  });

  it("o modo Vistos usa o contorno escuro e fino (entre 0,5 e 0,8 px)", () => {
    const { cor, largura } = contornoDosPaises("vistos");
    expect(cor).toBe("#1F2A44");
    expect(largura).toBeGreaterThanOrEqual(0.5);
    expect(largura).toBeLessThanOrEqual(0.8);
  });
});

describe("contraste do contorno do modo Vistos (WCAG 1.4.11, mínimo 3:1)", () => {
  const contorno = rgbDeHex(COR_DO_CONTORNO_NO_MODO_VISTOS);
  const contra = (hex: string) => contraste(contorno, rgbDeHex(hex));

  it("contra o oceano e o Brasil", () => {
    expect(contra(COR_DO_OCEANO)).toBeGreaterThanOrEqual(3);
    expect(contra(COR_DO_BRASIL_NO_MODO_VISTOS)).toBeGreaterThanOrEqual(3);
  });

  it("contra cada cor de visto, menos o 'Visto exigido', coberto pelo preenchimento contra o oceano", () => {
    for (const [situacao, cor] of Object.entries(CORES_DE_VISTO)) {
      if (situacao === "visto_exigido") continue;
      expect(contra(cor), situacao).toBeGreaterThanOrEqual(3);
    }
    expect(
      contraste(rgbDeHex(CORES_DE_VISTO.visto_exigido), rgbDeHex(COR_DO_OCEANO)),
    ).toBeGreaterThanOrEqual(3);
  });
});

describe("contornoDosPaises com o modo daltonismo (FR-008a)", () => {
  it("'Alertas' ligado usa o contorno do modo Vistos", () => {
    expect(contornoDosPaises("alertas", true)).toEqual(CONTORNO_DO_MODO_VISTOS);
  });

  it("'Alertas' desligado segue branco", () => {
    expect(contornoDosPaises("alertas", false)).toEqual({ cor: "#ffffff", largura: 0.6 });
  });

  it("'Vistos' é escuro nos dois estados", () => {
    expect(contornoDosPaises("vistos", false)).toEqual(CONTORNO_DO_MODO_VISTOS);
    expect(contornoDosPaises("vistos", true)).toEqual(CONTORNO_DO_MODO_VISTOS);
  });

  it("tem pelo menos 3:1 contra as quatro cores de Alertas e o oceano", () => {
    const contorno = rgbDeHex(contornoDosPaises("alertas", true).cor);
    for (const cor of [...Object.values(paletaDe(true).niveis), COR_DO_OCEANO]) {
      expect(contraste(contorno, rgbDeHex(cor)), cor).toBeGreaterThanOrEqual(3);
    }
  });
});

describe("transicaoDoContorno (research D9)", () => {
  it("com movimento reduzido, a troca sai sem animação", () => {
    expect(transicaoDoContorno(true)).toEqual({ duration: 0, delay: 0 });
  });

  it("sem essa preferência, fica a transição padrão do mapa", () => {
    expect(transicaoDoContorno(false)).toBeNull();
  });
});
