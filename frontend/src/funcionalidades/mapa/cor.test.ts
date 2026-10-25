import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { NIVEIS, type NivelId } from "../../compartilhado/niveis";
import type { Regiao } from "../../servicos/api/cliente";
import { COR_DA_AREA_NEUTRA, COR_DA_BORDA_REGIONAL, bordaRegionalDe, corDoTerritorio } from "./cor";

const regiao = (nome: string, nivel: Regiao["nivel"]): Regiao => ({ nome, nivel });

describe("corDoTerritorio", () => {
  it.each<[NivelId, string]>([
    ["sem_alerta", "#C0DD97"],
    ["evitar", "#FAC775"],
    ["nao_viajar", "#E24B4A"],
    ["nao_verificado", "#D3D1C7"],
  ])("o nível %s tem a cor %s", (nivel, cor) => {
    expect(corDoTerritorio("pais", nivel)).toBe(cor);
    expect(corDoTerritorio("dependencia", nivel)).toBe(cor);
  });

  it("usa a cor de cada nível definida em niveis.ts", () => {
    for (const nivel of Object.keys(NIVEIS) as NivelId[]) {
      expect(corDoTerritorio("pais", nivel)).toBe(NIVEIS[nivel].cor);
    }
  });

  it("sem informação do nível o padrão é não verificado, nunca sem alerta", () => {
    expect(corDoTerritorio("pais", undefined)).toBe(NIVEIS.nao_verificado.cor);
    expect(corDoTerritorio("dependencia", undefined)).not.toBe(NIVEIS.sem_alerta.cor);
  });

  it("área neutra tem cor própria, mesmo que alguém lhe passe um nível", () => {
    expect(corDoTerritorio("neutro", undefined)).toBe(COR_DA_AREA_NEUTRA);
    expect(corDoTerritorio("neutro", "nao_viajar")).toBe(COR_DA_AREA_NEUTRA);
  });

  it("a área neutra não se confunde com nenhum nível", () => {
    const cores = Object.values(NIVEIS).map((n) => n.cor.toLowerCase());
    expect(cores).not.toContain(COR_DA_AREA_NEUTRA.toLowerCase());
  });
});

describe("bordaRegionalDe", () => {
  it("sem regiões não há borda", () => {
    expect(bordaRegionalDe([])).toBeNull();
  });

  it("uma região de 'evite' dá a borda de 'evite'", () => {
    expect(bordaRegionalDe([regiao("Norte", "evitar")])).toBe("evitar");
  });

  it("uma região de 'não viaje' dá a borda de 'não viaje'", () => {
    expect(bordaRegionalDe([regiao("Sul do Líbano", "nao_viajar")])).toBe("nao_viajar");
  });

  it("com regiões dos dois tipos, vale a mais grave", () => {
    const regioes = [regiao("A", "evitar"), regiao("B", "nao_viajar"), regiao("C", "evitar")];
    expect(bordaRegionalDe(regioes)).toBe("nao_viajar");
  });
});

describe("cores da borda regional", () => {
  it("'não viaje' e 'evite' têm bordas diferentes entre si", () => {
    expect(COR_DA_BORDA_REGIONAL.nao_viajar).not.toBe(COR_DA_BORDA_REGIONAL.evitar);
  });

  it("repetem os tokens de tema.css", () => {
    const css = readFileSync(join(process.cwd(), "src/compartilhado/tema.css"), "utf-8");
    const token = (nome: string) =>
      new RegExp(`--color-${nome}:\\s*(#[0-9a-fA-F]{6})`).exec(css)?.[1]?.toLowerCase();
    expect(token("borda-regional-nao-viaje")).toBe(COR_DA_BORDA_REGIONAL.nao_viajar.toLowerCase());
    expect(token("borda-regional-evite")).toBe(COR_DA_BORDA_REGIONAL.evitar.toLowerCase());
    expect(token("area-neutra")).toBe(COR_DA_AREA_NEUTRA.toLowerCase());
  });
});
