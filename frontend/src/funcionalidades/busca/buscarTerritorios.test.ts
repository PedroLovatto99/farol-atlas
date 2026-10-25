import { describe, expect, it } from "vitest";
import type { TerritorioNoMapa } from "../../servicos/api/cliente";
import { buscarTerritorios, normalizar } from "./buscarTerritorios";

function territorio(
  codigo: string,
  nome: string,
  extras: Partial<TerritorioNoMapa> = {},
): TerritorioNoMapa {
  return {
    codigo,
    nome,
    rotulo_busca: nome,
    termos_busca: [],
    tipo: "pais",
    soberano: null,
    bandeira: codigo,
    identidade_do_soberano: false,
    nivel: "sem_alerta",
    regioes: [],
    observacao: null,
    ...extras,
  };
}

const TERRITORIOS: TerritorioNoMapa[] = [
  territorio("MX", "México"),
  territorio("DK", "Dinamarca"),
  territorio("GL", "Groenlândia (Dinamarca)", { tipo: "dependencia", soberano: "DK" }),
  territorio("GR", "Grécia"),
  territorio("VA", "Vaticano"),
  territorio("MC", "Mônaco"),
  territorio("RS", "Sérvia"),
  territorio("XK", "Sérvia", {
    rotulo_busca: "Kosovo (Sérvia)",
    termos_busca: ["Kosovo"],
    tipo: "dependencia",
    soberano: "RS",
    identidade_do_soberano: true,
  }),
  territorio("AR", "Argentina"),
  territorio("FK", "Argentina", {
    rotulo_busca: "Malvinas (Argentina)",
    termos_busca: ["Malvinas", "Ilhas Malvinas", "Falkland"],
    tipo: "dependencia",
    soberano: "AR",
    identidade_do_soberano: true,
  }),
];

const codigos = (termo: string) => buscarTerritorios(TERRITORIOS, termo).map((r) => r.codigo);
const rotulos = (termo: string) => buscarTerritorios(TERRITORIOS, termo).map((r) => r.rotulo);

describe("normalizar", () => {
  it("tira acentos, ignora maiúsculas e apara espaços", () => {
    expect(normalizar("  GROENLÂNDIA ")).toBe("groenlandia");
    expect(normalizar("Mônaco")).toBe("monaco");
  });
});

describe("buscarTerritorios", () => {
  it("ignora acentos e diferença de maiúsculas", () => {
    expect(codigos("mexi")).toEqual(["MX"]);
    expect(codigos("MEXICO")).toEqual(["MX"]);
    expect(codigos("méxi")).toEqual(["MX"]);
  });

  it("'gro' e 'groenlandia' encontram 'Groenlândia (Dinamarca)'", () => {
    expect(rotulos("gro")).toContain("Groenlândia (Dinamarca)");
    expect(rotulos("groenlandia")).toEqual(["Groenlândia (Dinamarca)"]);
  });

  it("encontra países muito pequenos: Vaticano e Mônaco", () => {
    expect(codigos("vaticano")).toEqual(["VA"]);
    expect(codigos("monaco")).toEqual(["MC"]);
  });

  it("'kosovo' encontra XK pelo termo de busca, com o rótulo 'Kosovo (Sérvia)'", () => {
    expect(buscarTerritorios(TERRITORIOS, "kosovo")).toEqual([
      { codigo: "XK", rotulo: "Kosovo (Sérvia)" },
    ]);
  });

  it("'malvinas' e 'ilhas malvinas' encontram FK, com o rótulo 'Malvinas (Argentina)'", () => {
    expect(buscarTerritorios(TERRITORIOS, "malvinas")).toEqual([
      { codigo: "FK", rotulo: "Malvinas (Argentina)" },
    ]);
    expect(codigos("ilhas malvinas")).toEqual(["FK"]);
  });

  it("não repete um território que casa por mais de um campo", () => {
    expect(codigos("malvinas").filter((c) => c === "FK")).toHaveLength(1);
  });

  it("quem começa com o termo vem antes de quem só contém o termo", () => {
    // "din" começa "Dinamarca" e só aparece dentro de "Groenlândia (Dinamarca)"
    expect(codigos("din")).toEqual(["DK", "GL"]);
  });

  it("busca vazia ou só com espaços não sugere nada", () => {
    expect(codigos("")).toEqual([]);
    expect(codigos("   ")).toEqual([]);
  });

  it("termo sem correspondência devolve lista vazia", () => {
    expect(codigos("xyzzy")).toEqual([]);
  });

  it("limita o número de sugestões", () => {
    const muitos = Array.from({ length: 30 }, (_, i) => territorio(`A${i}`, `Ilha ${i}`));
    expect(buscarTerritorios(muitos, "ilha").length).toBeLessThanOrEqual(8);
  });
});
