import { describe, expect, it } from "vitest";
import type { Mapa } from "../../servicos/api/cliente";
import { MAPA_EXEMPLO } from "../../testes/dados-exemplo";
import { responsavelDe } from "./responsavel";

const MAPA: Mapa = {
  ...MAPA_EXEMPLO,
  postos: [
    ...MAPA_EXEMPLO.postos,
    {
      id: 90,
      territorio: "US",
      tipo: "Consulado-Geral",
      cidade: "Miami",
      latitude: 25.76,
      longitude: -80.19,
      grupo: "25.76,-80.19",
    },
  ],
  paises_sem_posto: [
    { territorio: "PR", latitude: 18.2, longitude: -66.5, posto_responsavel_id: 90 },
    { territorio: "LY", latitude: 27, longitude: 17, posto_responsavel_id: null },
  ],
};

describe("responsavelDe", () => {
  it("devolve a coordenada do posto responsável de um país sem posto", () => {
    expect(responsavelDe(MAPA, "PR")).toEqual({
      latitude: 25.76,
      longitude: -80.19,
      grupo: "25.76,-80.19",
    });
  });

  it("devolve nulo para país com posto próprio", () => {
    expect(responsavelDe(MAPA, "DK")).toBeNull();
  });

  it("devolve nulo quando não há posto indicado (Líbia)", () => {
    expect(responsavelDe(MAPA, "LY")).toBeNull();
  });

  it("devolve nulo se o posto indicado não está na lista de postos", () => {
    const semPostos: Mapa = { ...MAPA, postos: [] };
    expect(responsavelDe(semPostos, "PR")).toBeNull();
  });
});
