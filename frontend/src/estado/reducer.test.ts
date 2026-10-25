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

describe("estado: filtro por nível (FR-024 a FR-026)", () => {
  it("desmarcar um nível o tira da lista de marcados", () => {
    const estado = reducer(ESTADO_INICIAL, { tipo: "alternar-nivel", nivel: "sem_alerta" });
    expect(estado.niveisMarcados).not.toContain("sem_alerta");
    expect(estado.niveisMarcados).toHaveLength(ORDEM_DA_LEGENDA.length - 1);
  });

  it("marcar de novo devolve o nível", () => {
    const sem = reducer(ESTADO_INICIAL, { tipo: "alternar-nivel", nivel: "evitar" });
    const volta = reducer(sem, { tipo: "alternar-nivel", nivel: "evitar" });
    expect([...volta.niveisMarcados].sort()).toEqual([...ORDEM_DA_LEGENDA].sort());
  });

  it("'marcar todos' devolve todos os níveis depois de desmarcar tudo", () => {
    let estado = ESTADO_INICIAL;
    for (const nivel of ORDEM_DA_LEGENDA) {
      estado = reducer(estado, { tipo: "alternar-nivel", nivel });
    }
    expect(estado.niveisMarcados).toEqual([]);
    const todos = reducer(estado, { tipo: "marcar-todos-niveis" });
    expect([...todos.niveisMarcados].sort()).toEqual([...ORDEM_DA_LEGENDA].sort());
  });

  it("mexer no filtro não mexe na seleção nem nos postos", () => {
    const aberto = {
      ...ESTADO_INICIAL,
      selecionado: "DK",
      postosExpandidos: [1],
      grupoEmDestaque: "a",
    };
    const estado = reducer(aberto, { tipo: "alternar-nivel", nivel: "evitar" });
    expect(estado).toMatchObject({
      selecionado: "DK",
      postosExpandidos: [1],
      grupoEmDestaque: "a",
    });
  });

  it("'marcar todos' com tudo marcado não muda o estado", () => {
    expect(reducer(ESTADO_INICIAL, { tipo: "marcar-todos-niveis" })).toBe(ESTADO_INICIAL);
  });
});

describe("estado: postos expandidos e destaque do ícone (FR-018a a FR-018g)", () => {
  const COM_DK = { ...ESTADO_INICIAL, selecionado: "DK" };

  it("expandir um posto o guarda e põe o ícone dele em destaque", () => {
    const estado = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    expect(estado.postosExpandidos).toEqual([1]);
    expect(estado.grupoEmDestaque).toBe("a");
  });

  it("só um ícone fica em destaque por vez: o último posto expandido", () => {
    const um = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const dois = reducer(um, { tipo: "expandir-posto", id: 2, grupo: "b" });
    expect(dois.postosExpandidos).toEqual([1, 2]);
    expect(dois.grupoEmDestaque).toBe("b");
  });

  it("expandir de novo o mesmo posto não muda nada (o evento do navegador se repete)", () => {
    const um = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    expect(reducer(um, { tipo: "expandir-posto", id: 1, grupo: "a" })).toBe(um);
  });

  it("recolher o posto em destaque tira o destaque", () => {
    const aberto = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const estado = reducer(aberto, { tipo: "recolher-posto", id: 1, grupo: "a" });
    expect(estado.postosExpandidos).toEqual([]);
    expect(estado.grupoEmDestaque).toBeNull();
  });

  it("recolher um posto que não está em destaque não tira o destaque do outro", () => {
    const um = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const dois = reducer(um, { tipo: "expandir-posto", id: 2, grupo: "b" });
    const estado = reducer(dois, { tipo: "recolher-posto", id: 1, grupo: "a" });
    expect(estado.postosExpandidos).toEqual([2]);
    expect(estado.grupoEmDestaque).toBe("b");
  });

  it("recolher um posto que já está recolhido não muda nada", () => {
    expect(reducer(COM_DK, { tipo: "recolher-posto", id: 9, grupo: "z" })).toBe(COM_DK);
  });

  it("fechar o painel remove o destaque e os postos expandidos", () => {
    const aberto = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const estado = reducer(aberto, { tipo: "limpar-selecao" });
    expect(estado.grupoEmDestaque).toBeNull();
    expect(estado.postosExpandidos).toEqual([]);
  });

  it("tocar num ícone seleciona o país do posto, com o posto expandido e em destaque", () => {
    const estado = reducer(ESTADO_INICIAL, {
      tipo: "tocar-icone",
      territorio: "US",
      grupo: "g",
      ids: [89],
    });
    expect(estado).toMatchObject({
      selecionado: "US",
      postosExpandidos: [89],
      grupoEmDestaque: "g",
    });
  });

  it("tocar num ícone compartilhado por dois postos expande os dois", () => {
    const estado = reducer(ESTADO_INICIAL, {
      tipo: "tocar-icone",
      territorio: "US",
      grupo: "g",
      ids: [89, 90],
    });
    expect(estado.postosExpandidos).toEqual([89, 90]);
    expect(estado.grupoEmDestaque).toBe("g");
  });

  it("tocar num ícone de outro país troca o painel e os postos expandidos", () => {
    const comDk = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const estado = reducer(comDk, {
      tipo: "tocar-icone",
      territorio: "US",
      grupo: "g",
      ids: [89],
    });
    expect(estado.selecionado).toBe("US");
    expect(estado.postosExpandidos).toEqual([89]);
    expect(estado.grupoEmDestaque).toBe("g");
  });

  it("expandir o posto responsável de um país sem posto destaca o ícone dele, em outro país", () => {
    const semPosto = { ...ESTADO_INICIAL, selecionado: "PR" };
    const estado = reducer(semPosto, { tipo: "expandir-posto", id: 91, grupo: "miami" });
    expect(estado.selecionado).toBe("PR");
    expect(estado.grupoEmDestaque).toBe("miami");
  });

  it("selecionar outro território depois de expandir limpa o destaque", () => {
    const aberto = reducer(COM_DK, { tipo: "expandir-posto", id: 1, grupo: "a" });
    const estado = reducer(aberto, { tipo: "selecionar", codigo: "US" });
    expect(estado.grupoEmDestaque).toBeNull();
    expect(estado.postosExpandidos).toEqual([]);
  });
});
