import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { simularMatchMedia, type MediaSimulada } from "../testes/match-media";
import { useTelaPequena } from "./useTelaPequena";

const CONSULTA = "(max-width: 700px)";
let media: MediaSimulada;

afterEach(() => media.restaurar());

describe("useTelaPequena", () => {
  it("é verdadeiro em telas de até 700 px (celular)", () => {
    media = simularMatchMedia({ [CONSULTA]: true });
    const { result } = renderHook(() => useTelaPequena());
    expect(result.current).toBe(true);
  });

  it("é falso em telas maiores", () => {
    media = simularMatchMedia({ [CONSULTA]: false });
    const { result } = renderHook(() => useTelaPequena());
    expect(result.current).toBe(false);
  });

  it("reage quando a largura muda", () => {
    media = simularMatchMedia({ [CONSULTA]: false });
    const { result } = renderHook(() => useTelaPequena());
    act(() => media.definir(CONSULTA, true));
    expect(result.current).toBe(true);
  });
});
