import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { contraste, rgbDeHex } from "../../compartilhado/contraste";
import {
  distanciaEntreCores,
  labDeRgb,
  simularDaltonismo,
  type TipoDeDaltonismo,
} from "../../compartilhado/distanciaDeCor";
import { NIVEIS, type NivelId } from "../../compartilhado/niveis";
import type { Regiao } from "../../servicos/api/cliente";
import {
  COR_DAS_LISTRAS,
  COR_DO_BRASIL_NO_MODO_VISTOS,
  COR_DO_OCEANO,
  CORES_DE_VISTO,
} from "../../compartilhado/vistos";
import type { SituacaoNoGlobo } from "../../servicos/api/cliente";
import {
  COR_DA_AREA_NEUTRA,
  COR_DA_BORDA_REGIONAL,
  COR_DAS_MARCAS,
  SEM_PREENCHIMENTO,
  bordaRegionalDe,
  corDoTerritorio,
  paletaDe,
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

describe("paletaDe: modo desligado (FR-015)", () => {
  const paleta = paletaDe(false);

  it("é igual às constantes atuais", () => {
    for (const nivel of Object.keys(NIVEIS) as NivelId[]) {
      expect(paleta.niveis[nivel]).toBe(NIVEIS[nivel].cor);
    }
    expect(paleta.bordas).toEqual(COR_DA_BORDA_REGIONAL);
    expect(paleta.vistos).toEqual(CORES_DE_VISTO);
    expect(paleta.listras).toBe(COR_DAS_LISTRAS);
  });
});

describe("paletaDe: modo ligado (contrato paletas-e-padroes.md)", () => {
  const paleta = paletaDe(true);

  it("traz as cores do contrato", () => {
    expect(paleta.niveis).toEqual({
      sem_alerta: "#8CCDFB",
      evitar: "#F1D25F",
      nao_viajar: "#E4605B",
      nao_verificado: "#878C92",
    });
    expect(paleta.bordas).toEqual({ nao_viajar: "#861212", evitar: "#8C641A" });
    expect(paleta.listras).toBe("#0E2A20");
    expect(COR_DAS_MARCAS).toBe("#18142C");
  });

  it("mantém as seis cores de Vistos", () => {
    expect(paleta.vistos).toEqual(CORES_DE_VISTO);
  });

  it("repete os tokens de tema.css", () => {
    const css = readFileSync(join(process.cwd(), "src/compartilhado/tema.css"), "utf-8");
    const token = (nome: string) =>
      new RegExp(`--color-daltonismo-${nome}:\\s*(#[0-9a-fA-F]{6})`).exec(css)?.[1]?.toUpperCase();
    expect(token("sem-alerta")).toBe(paleta.niveis.sem_alerta);
    expect(token("evitar")).toBe(paleta.niveis.evitar);
    expect(token("nao-viajar")).toBe(paleta.niveis.nao_viajar);
    expect(token("nao-verificado")).toBe(paleta.niveis.nao_verificado);
    expect(token("borda-nao-viaje")).toBe(paleta.bordas.nao_viajar);
    expect(token("borda-evite")).toBe(paleta.bordas.evitar);
    expect(token("marcas")).toBe(COR_DAS_MARCAS);
    expect(token("listras")).toBe(paleta.listras);
  });
});

describe("distâncias do modo ligado (FR-006, FR-007, SC-001)", () => {
  const paleta = paletaDe(true);
  const FIXAS = { neutro: COR_DO_BRASIL_NO_MODO_VISTOS, oceano: COR_DO_OCEANO };
  const ALERTAS: Readonly<Record<string, string>> = {
    ...paleta.niveis,
    borda_nao_viaje: paleta.bordas.nao_viajar,
    borda_evite: paleta.bordas.evitar,
    marcas: COR_DAS_MARCAS,
    ...FIXAS,
  };
  const VISTOS: Readonly<Record<string, string>> = {
    ...paleta.vistos,
    listras: paleta.listras,
    ...FIXAS,
  };
  const SIMULACOES: readonly TipoDeDaltonismo[] = ["protanopia", "deuteranopia", "tritanopia"];

  /** Todos os pares, menos neutro × oceano, que a spec deixa fora: não mudam e o contorno os separa. */
  function pares(cores: Readonly<Record<string, string>>): [string, string, string, string][] {
    const nomes = Object.keys(cores);
    return nomes
      .flatMap((a, i) => nomes.slice(i + 1).map((b) => [a, b] as const))
      .filter(([a, b]) => !(a === "neutro" && b === "oceano"))
      .map(([a, b]) => [a, b, cores[a]!, cores[b]!]);
  }

  function menorDistancia(a: string, b: string): number {
    const [ra, rb] = [rgbDeHex(a), rgbDeHex(b)];
    return Math.min(
      distanciaEntreCores(ra, rb),
      ...SIMULACOES.map((tipo) =>
        distanciaEntreCores(simularDaltonismo(ra, tipo), simularDaltonismo(rb, tipo)),
      ),
    );
  }

  it("são 35 pares em cada modo", () => {
    expect(pares(ALERTAS)).toHaveLength(35);
    expect(pares(VISTOS)).toHaveLength(35);
  });

  it.each(pares(ALERTAS))("Alertas: %s × %s fica a pelo menos 12", (_a, _b, corA, corB) => {
    expect(menorDistancia(corA, corB)).toBeGreaterThanOrEqual(12);
  });

  it.each(pares(VISTOS))("Vistos: %s × %s fica a pelo menos 12", (_a, _b, corA, corB) => {
    expect(menorDistancia(corA, corB)).toBeGreaterThanOrEqual(12);
  });

  it("a pior distância é a do contrato: 13,4 em Alertas e 12,1 em Vistos", () => {
    const pior = (cores: Readonly<Record<string, string>>) =>
      Math.min(...pares(cores).map(([, , a, b]) => menorDistancia(a, b)));
    expect(pior(ALERTAS)).toBeCloseTo(13.4, 1);
    expect(pior(VISTOS)).toBeCloseTo(12.1, 1);
  });
});

describe("bordas regionais do modo ligado (FR-008)", () => {
  const { bordas } = paletaDe(true);

  function matizECroma(hex: string): { matiz: number; croma: number } {
    const [, a, b] = labDeRgb(rgbDeHex(hex));
    return { matiz: (Math.atan2(b, a) * 180) / Math.PI, croma: Math.hypot(a, b) };
  }

  it("a de 'não viaje' continua vermelha", () => {
    const { matiz, croma } = matizECroma(bordas.nao_viajar);
    expect(matiz).toBeGreaterThanOrEqual(15);
    expect(matiz).toBeLessThanOrEqual(45);
    expect(croma).toBeGreaterThanOrEqual(40);
  });

  it("a de 'evite' continua marrom", () => {
    const { matiz, croma } = matizECroma(bordas.evitar);
    expect(matiz).toBeGreaterThanOrEqual(55);
    expect(matiz).toBeLessThanOrEqual(85);
    expect(croma).toBeGreaterThanOrEqual(25);
    expect(croma).toBeLessThanOrEqual(55);
  });
});

describe("contraste de marcas, listras e bordas do modo ligado (mínimo 3:1)", () => {
  const paleta = paletaDe(true);
  const entre = (a: string, b: string) => contraste(rgbDeHex(a), rgbDeHex(b));

  it("marcas sobre 'não viaje' e 'evite'", () => {
    expect(entre(COR_DAS_MARCAS, paleta.niveis.nao_viajar)).toBeGreaterThanOrEqual(3);
    expect(entre(COR_DAS_MARCAS, paleta.niveis.evitar)).toBeGreaterThanOrEqual(3);
  });

  it("listras sobre 'Isento'", () => {
    expect(entre(paleta.listras, paleta.vistos.isento)).toBeGreaterThanOrEqual(3);
  });

  it("bordas sobre 'sem alerta', 'evite' e o oceano", () => {
    for (const fundo of [paleta.niveis.sem_alerta, paleta.niveis.evitar, COR_DO_OCEANO]) {
      expect(entre(paleta.bordas.nao_viajar, fundo)).toBeGreaterThanOrEqual(3);
      expect(entre(paleta.bordas.evitar, fundo)).toBeGreaterThanOrEqual(3);
    }
  });
});

describe("preenchimentos com o modo ligado", () => {
  it.each<[NivelId, string, "nao_viajar" | "evitar" | null]>([
    ["sem_alerta", "#8CCDFB", null],
    ["evitar", "#F1D25F", "evitar"],
    ["nao_viajar", "#E4605B", "nao_viajar"],
    ["nao_verificado", "#878C92", null],
  ])("%s: cor %s e padrão %s", (nivel, cor, padrao) => {
    expect(preenchimentoDeAlerta("pais", nivel, true)).toEqual({ cor, padrao });
  });

  it("com o modo desligado nenhum nível tem padrão (FR-011)", () => {
    for (const nivel of Object.keys(NIVEIS) as NivelId[]) {
      expect(preenchimentoDeAlerta("pais", nivel, false).padrao).toBeNull();
    }
  });

  it("sem nível vale o cinza de 'não verificado' da paleta, sem padrão", () => {
    expect(preenchimentoDeAlerta("pais", undefined, true)).toEqual({
      cor: "#878C92",
      padrao: null,
    });
  });

  it("área neutra não muda de cor e nunca tem padrão", () => {
    expect(preenchimentoDeAlerta("neutro", "nao_viajar", true)).toEqual({
      cor: COR_DA_AREA_NEUTRA,
      padrao: null,
    });
    expect(corDoTerritorio("neutro", undefined, true)).toBe(COR_DA_AREA_NEUTRA);
  });

  it("'Vistos' mantém o padrão 'rg' e as cores nos dois estados", () => {
    for (const ligado of [false, true]) {
      expect(preenchimentoDeVisto("pais", "isento", true, ligado)).toEqual({
        cor: "#FEDD50",
        padrao: "rg",
      });
      expect(preenchimentoDeVisto("pais", "visto_exigido", false, ligado)).toEqual({
        cor: "#3B1C6B",
        padrao: null,
      });
      expect(preenchimentoDeVisto("pais", null, false, ligado)).toEqual(SEM_PREENCHIMENTO);
    }
  });
});
