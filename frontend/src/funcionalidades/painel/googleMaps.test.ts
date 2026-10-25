import { describe, expect, it } from "vitest";
import { urlDoGoogleMaps } from "./googleMaps";

function consulta(url: string): string {
  const endereco = new URL(url);
  expect(endereco.origin + endereco.pathname).toBe("https://www.google.com/maps/search/");
  expect(endereco.searchParams.get("api")).toBe("1");
  return endereco.searchParams.get("query") ?? "";
}

describe("urlDoGoogleMaps", () => {
  it("com endereço, usa o endereço", () => {
    const url = urlDoGoogleMaps({
      tipo: "Embaixada",
      cidade: "Copenhague",
      pais: "Dinamarca",
      endereco: "Kristianiagade 3, 2100 Copenhague",
    });
    expect(consulta(url)).toBe("Kristianiagade 3, 2100 Copenhague");
  });

  it("sem endereço, leva à cidade: tipo do Brasil, cidade, país", () => {
    const url = urlDoGoogleMaps({
      tipo: "Consulado-Geral",
      cidade: "Milão",
      pais: "Itália",
      endereco: null,
    });
    expect(consulta(url)).toBe("Consulado-Geral do Brasil, Milão, Itália");
  });

  it("endereço em branco conta como ausente", () => {
    const url = urlDoGoogleMaps({
      tipo: "Embaixada",
      cidade: "Lima",
      pais: "Peru",
      endereco: "   ",
    });
    expect(consulta(url)).toBe("Embaixada do Brasil, Lima, Peru");
  });

  it("vale também para o posto responsável, que fica em outro país", () => {
    const url = urlDoGoogleMaps({
      tipo: "Consulado-Geral",
      cidade: "Miami",
      pais: "Estados Unidos",
      endereco: null,
    });
    expect(consulta(url)).toBe("Consulado-Geral do Brasil, Miami, Estados Unidos");
  });

  it("codifica a URL: texto com & # ? e acentos não quebra a consulta", () => {
    const url = urlDoGoogleMaps({
      tipo: "Embaixada",
      cidade: "São Tomé",
      pais: "A&B?",
      endereco: "Rua #1 & Cia?x=y",
    });
    expect(url).not.toContain("#");
    expect(new URL(url).searchParams.get("query")).toBe("Rua #1 & Cia?x=y");
    expect(Array.from(new URL(url).searchParams.keys())).toEqual(["api", "query"]);
  });
});
