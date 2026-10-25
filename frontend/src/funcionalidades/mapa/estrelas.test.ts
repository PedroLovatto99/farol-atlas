import { describe, expect, it } from "vitest";
import {
  QUANTIDADE_DE_ESTRELAS,
  SEMENTE_DO_CEU,
  TAMANHO_DO_CEU,
  gerarEstrelas,
  type Estrela,
} from "./estrelas";

const doCeu = () => gerarEstrelas(SEMENTE_DO_CEU, QUANTIDADE_DE_ESTRELAS, TAMANHO_DO_CEU);

describe("estrelas do céu", () => {
  it("com a mesma semente sai sempre o mesmo céu", () => {
    expect(doCeu()).toEqual(doCeu());
  });

  it("com outra semente sai outro céu", () => {
    expect(gerarEstrelas(SEMENTE_DO_CEU + 1, QUANTIDADE_DE_ESTRELAS, TAMANHO_DO_CEU)).not.toEqual(
      doCeu(),
    );
  });

  it("gera a quantidade pedida, todas dentro do quadro", () => {
    const estrelas = doCeu();
    expect(estrelas).toHaveLength(QUANTIDADE_DE_ESTRELAS);
    for (const { x, y } of estrelas) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(x).toBeLessThan(TAMANHO_DO_CEU);
      expect(y).toBeGreaterThanOrEqual(0);
      expect(y).toBeLessThan(TAMANHO_DO_CEU);
    }
  });

  it("tamanhos variados: muitas pequenas, algumas médias e poucas brilhantes", () => {
    const estrelas = doCeu();
    const brilhantes = estrelas.filter((e) => e.brilhante);
    const pequenas = estrelas.filter((e) => e.raio < 1);
    expect(brilhantes.length).toBeGreaterThanOrEqual(5);
    expect(brilhantes.length).toBeLessThanOrEqual(QUANTIDADE_DE_ESTRELAS * 0.06);
    expect(pequenas.length).toBeGreaterThan(QUANTIDADE_DE_ESTRELAS * 0.6);
    expect(new Set(estrelas.map((e) => e.raio.toFixed(1))).size).toBeGreaterThanOrEqual(6);
  });

  it("as brilhantes são as maiores", () => {
    const estrelas: Estrela[] = doCeu();
    const menorBrilhante = Math.min(...estrelas.filter((e) => e.brilhante).map((e) => e.raio));
    const maiorComum = Math.max(...estrelas.filter((e) => !e.brilhante).map((e) => e.raio));
    expect(menorBrilhante).toBeGreaterThan(maiorComum);
  });

  it("a opacidade fica entre 0 e 1 e varia de estrela para estrela", () => {
    const estrelas = doCeu();
    for (const { opacidade } of estrelas) {
      expect(opacidade).toBeGreaterThan(0);
      expect(opacidade).toBeLessThanOrEqual(1);
    }
    expect(new Set(estrelas.map((e) => e.opacidade.toFixed(1))).size).toBeGreaterThanOrEqual(4);
  });
});
