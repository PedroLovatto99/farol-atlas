import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  CHAVE_DO_DALTONISMO,
  gravarPreferenciaDoDaltonismo,
  lerPreferenciaDoDaltonismo,
} from "./preferencia";

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("preferência do modo daltonismo", () => {
  it("usa a chave do contrato, sem 'modo' no nome", () => {
    expect(CHAVE_DO_DALTONISMO).toBe("farol-atlas:daltonismo");
  });

  it("'ligado' lê verdadeiro", () => {
    window.localStorage.setItem(CHAVE_DO_DALTONISMO, "ligado");
    expect(lerPreferenciaDoDaltonismo()).toBe(true);
  });

  it.each(["desligado", "true", "LIGADO", ""])("%j lê falso", (valor) => {
    window.localStorage.setItem(CHAVE_DO_DALTONISMO, valor);
    expect(lerPreferenciaDoDaltonismo()).toBe(false);
  });

  it("sem valor guardado lê falso", () => {
    expect(lerPreferenciaDoDaltonismo()).toBe(false);
  });

  it("grava 'ligado' e 'desligado'", () => {
    gravarPreferenciaDoDaltonismo(true);
    expect(window.localStorage.getItem(CHAVE_DO_DALTONISMO)).toBe("ligado");
    gravarPreferenciaDoDaltonismo(false);
    expect(window.localStorage.getItem(CHAVE_DO_DALTONISMO)).toBe("desligado");
  });

  it("armazenamento que lança erro não quebra a leitura nem a gravação", () => {
    const falha = () => {
      throw new Error("bloqueado");
    };
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(falha);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(falha);
    expect(lerPreferenciaDoDaltonismo()).toBe(false);
    expect(() => gravarPreferenciaDoDaltonismo(true)).not.toThrow();
  });
});
