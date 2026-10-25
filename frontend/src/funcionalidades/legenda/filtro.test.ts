import { describe, expect, it } from "vitest";
import { ORDEM_DA_LEGENDA, type NivelId } from "../../compartilhado/niveis";
import { alternarNivel, nenhumNivelMarcado, territorioEsmaecido } from "./filtro";

const TODOS = ORDEM_DA_LEGENDA;

describe("territorioEsmaecido", () => {
  it("com todos os níveis marcados nada esmaece", () => {
    for (const nivel of TODOS) {
      expect(territorioEsmaecido({ nivel, regioes: [] }, TODOS)).toBe(false);
    }
  });

  it("esmaece o território cujo nível está desmarcado", () => {
    const marcados: NivelId[] = ["evitar", "nao_viajar", "nao_verificado"];
    expect(territorioEsmaecido({ nivel: "sem_alerta", regioes: [] }, marcados)).toBe(true);
    expect(territorioEsmaecido({ nivel: "evitar", regioes: [] }, marcados)).toBe(false);
  });

  it("'não verificado' também esmaece quando desmarcado", () => {
    expect(territorioEsmaecido({ nivel: "nao_verificado", regioes: [] }, ["sem_alerta"])).toBe(
      true,
    );
  });

  it("Líbano com só 'não viaje' marcado não esmaece, por causa da região (FR-027)", () => {
    const libano = {
      nivel: "evitar" as const,
      regioes: [{ nome: "Sul do Líbano", nivel: "nao_viajar" as const }],
    };
    expect(territorioEsmaecido(libano, ["nao_viajar"])).toBe(false);
  });

  it("região de um nível desmarcado não salva o território", () => {
    const libano = {
      nivel: "evitar" as const,
      regioes: [{ nome: "Sul do Líbano", nivel: "nao_viajar" as const }],
    };
    expect(territorioEsmaecido(libano, ["sem_alerta"])).toBe(true);
    // a região é de "não viaje"; só "evite" marcado não a traz de volta
    expect(territorioEsmaecido({ nivel: "sem_alerta", regioes: libano.regioes }, ["evitar"])).toBe(
      true,
    );
  });

  it("neutros nunca esmaecem", () => {
    expect(territorioEsmaecido({ nivel: null, regioes: [] }, [])).toBe(false);
    expect(territorioEsmaecido({ nivel: null, regioes: [] }, ["nao_viajar"])).toBe(false);
  });

  it("com nenhum nível marcado todo território esmaece", () => {
    for (const nivel of TODOS) {
      expect(territorioEsmaecido({ nivel, regioes: [] }, [])).toBe(true);
    }
  });
});

describe("nenhumNivelMarcado", () => {
  it("é verdadeiro só quando a lista está vazia", () => {
    expect(nenhumNivelMarcado([])).toBe(true);
    expect(nenhumNivelMarcado(["evitar"])).toBe(false);
  });
});

describe("alternarNivel", () => {
  it("desmarca um nível marcado", () => {
    expect(alternarNivel(TODOS, "evitar")).not.toContain("evitar");
    expect(alternarNivel(TODOS, "evitar")).toHaveLength(TODOS.length - 1);
  });

  it("marca de novo um nível desmarcado, sem duplicar", () => {
    const sem = alternarNivel(TODOS, "evitar");
    const volta = alternarNivel(sem, "evitar");
    expect([...volta].sort()).toEqual([...TODOS].sort());
  });
});
