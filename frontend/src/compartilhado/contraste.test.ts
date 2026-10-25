import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { contraste, rgbDeHex, sobrepor } from "./contraste";

const tema = readFileSync(resolve(process.cwd(), "src/compartilhado/tema.css"), "utf-8");

function token(nome: string) {
  const achado = new RegExp(`--color-${nome}:\\s*(#[0-9a-fA-F]{3,6})`).exec(tema);
  if (achado?.[1] === undefined) throw new Error(`token --color-${nome} não está em tema.css`);
  return rgbDeHex(achado[1]);
}

describe("contraste (WCAG)", () => {
  it("bate com os valores de referência", () => {
    expect(contraste(rgbDeHex("#000000"), rgbDeHex("#ffffff"))).toBeCloseTo(21, 1);
    expect(contraste(rgbDeHex("#777777"), rgbDeHex("#ffffff"))).toBeCloseTo(4.48, 1);
    expect(contraste(rgbDeHex("#fff"), rgbDeHex("#fff"))).toBeCloseTo(1, 5);
  });

  it("sobrepor mistura a cor com o fundo pela opacidade", () => {
    expect(sobrepor([255, 255, 255], 0.5, [0, 0, 0])).toEqual([128, 128, 128]);
    expect(sobrepor([10, 20, 30], 1, [200, 200, 200])).toEqual([10, 20, 30]);
  });
});

/**
 * Tudo o que fica sobre o céu escuro ou sobre o globo claro (fora do globo é o céu; no zoom, o
 * mapa claro ocupa a tela toda). Mínimo AA: 4,5:1 para texto normal.
 */
describe("contraste do tema sobre o céu e sobre o mapa", () => {
  const ceu = token("ceu");
  const oceano = token("oceano");
  const branco = rgbDeHex("#ffffff");
  const AA = 4.5;

  it("o céu é quase preto", () => {
    expect(contraste(ceu, rgbDeHex("#000000"))).toBeLessThan(1.3);
  });

  it("o título do cabeçalho (texto branco sobre o céu a 90%) lê bem sobre o céu e sobre o mapa", () => {
    for (const debaixo of [ceu, oceano, token("nivel-sem-alerta")]) {
      expect(contraste(branco, sobrepor(ceu, 0.9, debaixo))).toBeGreaterThanOrEqual(AA);
    }
  });

  it("o botão Sobre (azul-marinho sobre branco a 90%) lê bem sobre o céu e sobre o mapa", () => {
    for (const debaixo of [ceu, oceano]) {
      expect(contraste(token("marinho"), sobrepor(branco, 0.9, debaixo))).toBeGreaterThanOrEqual(
        AA,
      );
    }
  });

  it("o aviso de site não oficial", () => {
    expect(contraste(token("aviso-texto"), token("aviso-fundo"))).toBeGreaterThanOrEqual(AA);
  });

  it("o texto dos cartões brancos (legenda, painel, busca)", () => {
    expect(contraste(token("texto-2"), branco)).toBeGreaterThanOrEqual(AA);
    expect(contraste(token("texto"), branco)).toBeGreaterThanOrEqual(AA);
  });

  it("o texto cinza do cartão de observação do painel (fundo claro espaco)", () => {
    expect(contraste(token("texto-2"), token("espaco"))).toBeGreaterThanOrEqual(AA);
  });
});
