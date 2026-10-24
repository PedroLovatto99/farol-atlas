import { describe, expect, it } from "vitest";
import { ORDEM_DA_LEGENDA } from "../compartilhado/niveis";
import { ESTADO_INICIAL, reducer } from "./reducer";

describe("estado da aplicação", () => {
  it("começa sem seleção e com todos os níveis marcados (FR-024)", () => {
    expect(ESTADO_INICIAL.selecionado).toBeNull();
    expect(ESTADO_INICIAL.postosExpandidos).toEqual([]);
    expect(ESTADO_INICIAL.grupoEmDestaque).toBeNull();
    expect([...ESTADO_INICIAL.niveisMarcados].sort()).toEqual([...ORDEM_DA_LEGENDA].sort());
  });

  it("selecionar um território guarda o código", () => {
    const estado = reducer(ESTADO_INICIAL, { tipo: "selecionar", codigo: "DK" });
    expect(estado.selecionado).toBe("DK");
  });

  it("selecionar outro território limpa postos expandidos e destaque", () => {
    const comPosto = {
      ...ESTADO_INICIAL,
      selecionado: "DK",
      postosExpandidos: [1],
      grupoEmDestaque: "55.6761,12.5683",
    };
    const estado = reducer(comPosto, { tipo: "selecionar", codigo: "PT" });
    expect(estado.selecionado).toBe("PT");
    expect(estado.postosExpandidos).toEqual([]);
    expect(estado.grupoEmDestaque).toBeNull();
  });

  it("limpar a seleção volta ao mundo, mas mantém os níveis marcados", () => {
    const comFiltro = {
      ...ESTADO_INICIAL,
      selecionado: "DK",
      niveisMarcados: ["nao_viajar" as const],
    };
    const estado = reducer(comFiltro, { tipo: "limpar-selecao" });
    expect(estado.selecionado).toBeNull();
    expect(estado.niveisMarcados).toEqual(["nao_viajar"]);
  });

  it("não muda o estado anterior (função pura)", () => {
    const antes = { ...ESTADO_INICIAL };
    reducer(ESTADO_INICIAL, { tipo: "selecionar", codigo: "DK" });
    expect(ESTADO_INICIAL).toEqual(antes);
  });
});
