import { describe, expect, it } from "vitest";
import { ehUrlWeb } from "./urlSegura";

describe("ehUrlWeb", () => {
  it("aceita http e https", () => {
    expect(ehUrlWeb("https://www.gov.br/mre/pt-br/alertas")).toBe(true);
    expect(ehUrlWeb("http://exemplo.org/a?b=c")).toBe(true);
  });

  it.each(["javascript:alert(1)", "data:text/html,<b>x</b>", "ftp://servidor/arquivo", "tel:123"])(
    "recusa %s",
    (url) => {
      expect(ehUrlWeb(url)).toBe(false);
    },
  );

  it("recusa o que não é um endereço", () => {
    expect(ehUrlWeb("")).toBe(false);
    expect(ehUrlWeb("www.gov.br")).toBe(false);
    expect(ehUrlWeb("/relativo")).toBe(false);
  });
});
