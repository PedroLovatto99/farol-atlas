import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// quebras de linha dentro dos seletores não importam
const tema = readFileSync(resolve(process.cwd(), "src/compartilhado/tema.css"), "utf-8").replace(
  /\s+/g,
  " ",
);

/** O corpo de cada regra cujo seletor contém o trecho dado. */
function regras(trecho: string): string[] {
  return Array.from(tema.matchAll(/([^{}]+)\{([^{}]*)\}/g))
    .filter((m) => (m[1] ?? "").includes(trecho))
    .map((m) => m[2] ?? "");
}

describe("tema.css: painel recolhido (FR-030)", () => {
  it("no celular os controles de zoom e a legenda sobem acima da barra", () => {
    const zoom = regras(
      '[data-painel-recolhido="true"][data-modo-do-painel="gaveta"] .maplibregl-ctrl-bottom-right',
    );
    const legenda = regras(
      '[data-painel-recolhido="true"][data-modo-do-painel="gaveta"] .legenda-flutuante',
    );
    expect(zoom).toHaveLength(1);
    expect(legenda).toHaveLength(1);
    expect(zoom[0]).toMatch(/bottom:\s*var\(--rodape-ocupado\)/);
    expect(legenda[0]).toMatch(/bottom:\s*calc\(var\(--rodape-ocupado\)/);
    expect(tema).toMatch(/--rodape-ocupado:\s*[\d.]+rem/);
  });

  it("no computador nenhum deslocamento: a barra fica no canto superior direito", () => {
    expect(regras('[data-painel-recolhido="true"][data-modo-do-painel="lateral"]')).toHaveLength(0);
  });

  it("as regras do painel aberto não valem com o painel recolhido", () => {
    const aberto = '[data-painel-aberto="true"]:not([data-painel-recolhido="true"])';
    expect(tema).toContain(
      `${aberto}[data-modo-do-painel="lateral"] .maplibregl-ctrl-bottom-right`,
    );
    expect(tema).toContain(`${aberto}[data-modo-do-painel="gaveta"] .maplibregl-ctrl-bottom-right`);
  });

  it("nenhuma animação ou transição nova no CSS do painel recolhido", () => {
    for (const corpo of regras("data-painel-recolhido")) {
      expect(corpo).not.toMatch(/transition|animation/);
    }
  });
});
