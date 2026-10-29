import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { NIVEIS, type NivelId } from "../../compartilhado/niveis";
import type { Regiao } from "../../servicos/api/cliente";
import { CORES_DE_VISTO } from "../../compartilhado/vistos";
import type { SituacaoNoGlobo } from "../../servicos/api/cliente";
import {
  COR_DA_AREA_NEUTRA,
  COR_DA_BORDA_REGIONAL,
  SEM_PREENCHIMENTO,
  bordaRegionalDe,
  corDoTerritorio,
  preenchimentoDeAlerta,
  preenchimentoDeVisto,
} from "./cor";

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

describe("preenchimentoDeAlerta (a 001 continua igual)", () => {
  it.each<[NivelId, string]>([
    ["sem_alerta", "#C0DD97"],
    ["evitar", "#FAC775"],
    ["nao_viajar", "#E24B4A"],
    ["nao_verificado", "#D3D1C7"],
  ])("o nível %s tem exatamente a cor %s, sem padrão", (nivel, cor) => {
    expect(preenchimentoDeAlerta("pais", nivel)).toEqual({ cor, padrao: null });
    expect(preenchimentoDeAlerta("dependencia", nivel)).toEqual({ cor, padrao: null });
  });

  it("sem nível o padrão é não verificado; área neutra tem a cor própria", () => {
    expect(preenchimentoDeAlerta("pais", undefined)).toEqual({ cor: "#D3D1C7", padrao: null });
    expect(preenchimentoDeAlerta("neutro", "nao_viajar")).toEqual({
      cor: COR_DA_AREA_NEUTRA,
      padrao: null,
    });
  });
});

describe("preenchimentoDeVisto", () => {
  it.each<[SituacaoNoGlobo, string]>([
    ["isento", "#FEDD50"],
    ["visto_na_chegada", "#D17DA4"],
    ["autorizacao_eletronica", "#8F5FCC"],
    ["visto_exigido", "#3B1C6B"],
    ["outra_situacao", "#948878"],
    ["sem_informacao", "#BEBAB1"],
  ])("%s é pintado com %s", (situacao, cor) => {
    expect(preenchimentoDeVisto("pais", situacao, false)).toEqual({ cor, padrao: null });
  });

  it("'Isento' que aceita só o RG leva a base do isento com o padrão 'rg'", () => {
    expect(preenchimentoDeVisto("pais", "isento", true)).toEqual({ cor: "#FEDD50", padrao: "rg" });
  });

  it("aceita_rg só vale para o 'Isento': nenhuma outra categoria ganha listras", () => {
    for (const situacao of [
      "visto_na_chegada",
      "autorizacao_eletronica",
      "visto_exigido",
      "outra_situacao",
      "sem_informacao",
    ] as const) {
      expect(preenchimentoDeVisto("pais", situacao, true).padrao).toBeNull();
    }
  });

  it("o Brasil e as áreas neutras ficam no neutro, distinto do cinza de 'sem informação'", () => {
    const neutro = { cor: "#F1EFE8", padrao: null };
    expect(preenchimentoDeVisto("pais", "nao_se_aplica", false)).toEqual(neutro);
    expect(preenchimentoDeVisto("neutro", "visto_exigido", false)).toEqual(neutro);
    expect(preenchimentoDeVisto("neutro", null, false)).toEqual(neutro);
    expect(neutro.cor).not.toBe(CORES_DE_VISTO.sem_informacao);
  });

  it("sem situação (carregando ou erro) o território fica sem preenchimento, nunca em cinza", () => {
    const resultado = preenchimentoDeVisto("pais", null, false);
    expect(resultado).toEqual(SEM_PREENCHIMENTO);
    expect(resultado.cor).toBeNull();
    expect(resultado.cor).not.toBe(CORES_DE_VISTO.sem_informacao);
  });

  it("nenhuma cor de visto é uma cor de alerta", () => {
    const alertas = Object.values(NIVEIS).map((n) => n.cor.toLowerCase());
    for (const cor of Object.values(CORES_DE_VISTO)) {
      expect(alertas).not.toContain(cor.toLowerCase());
    }
  });
});
