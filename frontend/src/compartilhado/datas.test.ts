import { describe, expect, it } from "vitest";
import { formatarData } from "./datas";

describe("formatarData", () => {
  it("formata data com hora no fuso de Brasília", () => {
    expect(formatarData("2026-08-17T15:00:00Z")).toBe("17/08/2026");
    expect(formatarData("2026-08-17T02:00:00Z")).toBe("16/08/2026"); // ainda é dia 16 no Brasil
  });

  it("formata data sem hora sem deslocar o dia", () => {
    expect(formatarData("2026-10-21")).toBe("21/10/2026");
  });

  it("devolve o texto original quando não é uma data", () => {
    expect(formatarData("ontem")).toBe("ontem");
  });
});
