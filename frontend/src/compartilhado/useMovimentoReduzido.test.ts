import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { simularMatchMedia, type MediaSimulada } from "../testes/match-media";
import { useMovimentoReduzido } from "./useMovimentoReduzido";

const CONSULTA = "(prefers-reduced-motion: reduce)";
let media: MediaSimulada;

afterEach(() => media.restaurar());

describe("useMovimentoReduzido", () => {
  it("é falso quando o sistema não pede movimento reduzido", () => {
    media = simularMatchMedia({ [CONSULTA]: false });
    const { result } = renderHook(() => useMovimentoReduzido());
    expect(result.current).toBe(false);
  });

  it("é verdadeiro quando o sistema pede movimento reduzido (FR-039)", () => {
    media = simularMatchMedia({ [CONSULTA]: true });
    const { result } = renderHook(() => useMovimentoReduzido());
    expect(result.current).toBe(true);
  });

  it("reage quando a preferência muda com o site aberto", () => {
    media = simularMatchMedia({ [CONSULTA]: false });
    const { result } = renderHook(() => useMovimentoReduzido());
    act(() => media.definir(CONSULTA, true));
    expect(result.current).toBe(true);
  });
});
