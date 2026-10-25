import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { limparCacheDaGeometria, useGeometria } from "./useGeometria";

const GEOMETRIA = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { codigo: "BO", soberano: null, tipo: "pais", titulo: "Bolívia", zoom: "BO" },
      geometry: { type: "Polygon", coordinates: [] },
    },
  ],
};

function respostaJson(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status });
}

afterEach(() => limparCacheDaGeometria());

describe("useGeometria", () => {
  it("carrega o arquivo de geometria", async () => {
    const buscar = vi.fn(() => Promise.resolve(respostaJson(GEOMETRIA)));
    const { result } = renderHook(() => useGeometria(buscar));

    expect(result.current.situacao).toBe("carregando");
    await waitFor(() => expect(result.current.situacao).toBe("pronto"));
    const estado = result.current;
    expect(estado.situacao === "pronto" && estado.geometria.features).toHaveLength(1);
  });

  it("carrega uma única vez, mesmo com vários componentes pedindo", async () => {
    const buscar = vi.fn(() => Promise.resolve(respostaJson(GEOMETRIA)));
    const a = renderHook(() => useGeometria(buscar));
    const b = renderHook(() => useGeometria(buscar));
    await waitFor(() => expect(a.result.current.situacao).toBe("pronto"));
    await waitFor(() => expect(b.result.current.situacao).toBe("pronto"));

    const c = renderHook(() => useGeometria(buscar)); // depois de carregada: sem nova chamada
    await waitFor(() => expect(c.result.current.situacao).toBe("pronto"));

    expect(buscar).toHaveBeenCalledTimes(1);
  });

  it("erro de rede vira erro e uma nova tentativa pode funcionar", async () => {
    const buscar = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new TypeError("falhou"))
      .mockResolvedValue(respostaJson(GEOMETRIA));

    const primeira = renderHook(() => useGeometria(buscar));
    await waitFor(() => expect(primeira.result.current.situacao).toBe("erro"));

    const segunda = renderHook(() => useGeometria(buscar));
    await waitFor(() => expect(segunda.result.current.situacao).toBe("pronto"));
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it("sem passar o buscar, não entra em laço de renderização (a função padrão é sempre a mesma)", async () => {
    // Regressão: a função padrão era recriada a cada render, o que refazia o efeito, que mudava o
    // estado, que renderizava de novo... sem parar. Com o painel na tela, isso travava o navegador.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(respostaJson(GEOMETRIA))),
    );
    try {
      let renderizacoes = 0;
      const { result } = renderHook(() => {
        renderizacoes += 1;
        return useGeometria();
      });
      await waitFor(() => expect(result.current.situacao).toBe("pronto"));
      await new Promise((resolver) => setTimeout(resolver, 100));
      const estavel = renderizacoes;
      await new Promise((resolver) => setTimeout(resolver, 100));

      expect(renderizacoes).toBe(estavel);
      expect(estavel).toBeLessThanOrEqual(4);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("HTTP de erro vira erro", async () => {
    const buscar = vi.fn(() => Promise.resolve(respostaJson({}, 404)));
    const { result } = renderHook(() => useGeometria(buscar));
    await waitFor(() => expect(result.current.situacao).toBe("erro"));
  });

  it.each([
    ["não é uma coleção", { type: "Feature" }],
    [
      "feição sem código",
      { type: "FeatureCollection", features: [{ type: "Feature", properties: {} }] },
    ],
    ["sem lista de feições", { type: "FeatureCollection" }],
  ])("recusa geometria inválida (%s)", async (_nome, corpo) => {
    const buscar = vi.fn(() => Promise.resolve(respostaJson(corpo)));
    const { result } = renderHook(() => useGeometria(buscar));
    await waitFor(() => expect(result.current.situacao).toBe("erro"));
  });
});
