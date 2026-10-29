import { describe, expect, it } from "vitest";
import { ORDEM_DA_LEGENDA } from "../compartilhado/niveis";
import { TODAS_AS_CHAVES_DE_VISTO } from "../compartilhado/vistos";
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

describe("estado: modo do globo e vistos (feature 002)", () => {
  const COM_TUDO = {
    ...ESTADO_INICIAL,
    selecionado: "DK",
    postosExpandidos: [1],
    grupoEmDestaque: "a",
    niveisMarcados: ["nao_viajar" as const],
  };

  it("o modo inicial é 'alertas' e os vistos ainda não foram pedidos", () => {
    expect(ESTADO_INICIAL.modo).toBe("alertas");
    expect(ESTADO_INICIAL.vistos).toEqual({ situacao: "nao_pedido" });
  });

  it("os vistos começam com todas as chaves marcadas, independentes dos níveis", () => {
    expect([...ESTADO_INICIAL.vistosMarcados].sort()).toEqual([...TODAS_AS_CHAVES_DE_VISTO].sort());
    const estado = reducer(ESTADO_INICIAL, { tipo: "alternar-nivel", nivel: "evitar" });
    expect(estado.vistosMarcados).toEqual(ESTADO_INICIAL.vistosMarcados);
  });

  it("trocar o modo não mexe na seleção, nos postos, no destaque nem nos filtros", () => {
    const estado = reducer(COM_TUDO, { tipo: "trocar-modo", modo: "vistos" });
    expect(estado.modo).toBe("vistos");
    expect(estado.selecionado).toBe("DK");
    expect(estado.postosExpandidos).toEqual([1]);
    expect(estado.grupoEmDestaque).toBe("a");
    expect(estado.niveisMarcados).toEqual(["nao_viajar"]);
    expect(estado.vistosMarcados).toEqual(COM_TUDO.vistosMarcados);
    expect(estado.vistos).toEqual(COM_TUDO.vistos);
  });

  it("voltar para 'alertas' devolve o modo e guarda o filtro de cada modo", () => {
    const emVistos = reducer(COM_TUDO, { tipo: "trocar-modo", modo: "vistos" });
    const semRg = reducer(emVistos, { tipo: "alternar-visto", chave: "isento_rg" });
    const volta = reducer(semRg, { tipo: "trocar-modo", modo: "alertas" });
    expect(volta.modo).toBe("alertas");
    expect(volta.niveisMarcados).toEqual(["nao_viajar"]);
    expect(volta.vistosMarcados).not.toContain("isento_rg");
  });

  it("alternar-visto desmarca e marca uma chave, e o pai leva o subitem", () => {
    const sem = reducer(ESTADO_INICIAL, { tipo: "alternar-visto", chave: "visto_exigido" });
    expect(sem.vistosMarcados).not.toContain("visto_exigido");
    expect(
      reducer(sem, { tipo: "alternar-visto", chave: "visto_exigido" }).vistosMarcados,
    ).toContain("visto_exigido");
    const pai = reducer(ESTADO_INICIAL, { tipo: "alternar-visto", chave: "isento" });
    expect(pai.vistosMarcados).not.toContain("isento");
    expect(pai.vistosMarcados).not.toContain("isento_rg");
  });

  it("alternar-visto não mexe nos níveis de alerta", () => {
    const estado = reducer(COM_TUDO, { tipo: "alternar-visto", chave: "isento" });
    expect(estado.niveisMarcados).toEqual(["nao_viajar"]);
  });

  it("marcar-todos-vistos remarca tudo (e não muda nada se já estava tudo marcado)", () => {
    const sem = reducer(ESTADO_INICIAL, { tipo: "alternar-visto", chave: "visto_exigido" });
    const todos = reducer(sem, { tipo: "marcar-todos-vistos" });
    expect([...todos.vistosMarcados].sort()).toEqual([...TODAS_AS_CHAVES_DE_VISTO].sort());
    expect(reducer(ESTADO_INICIAL, { tipo: "marcar-todos-vistos" })).toBe(ESTADO_INICIAL);
  });

  it("os vistos passam de 'nao_pedido' para 'carregando' e daí para 'pronto' ou 'erro'", () => {
    const carregando = reducer(ESTADO_INICIAL, { tipo: "vistos-carregando" });
    expect(carregando.vistos).toEqual({ situacao: "carregando" });
    const dados = {
      dados_obtidos: true,
      coletado_em: "2026-10-29T13:04:35Z",
      desatualizado: false,
      fonte: { nome: "Wikipédia", url: "https://en.wikipedia.org/wiki/X", licenca: "CC BY-SA" },
      territorios: [],
    };
    expect(reducer(carregando, { tipo: "vistos-carregados", dados }).vistos).toEqual({
      situacao: "pronto",
      dados,
    });
    expect(reducer(carregando, { tipo: "vistos-falhou", mensagem: "caiu" }).vistos).toEqual({
      situacao: "erro",
      mensagem: "caiu",
    });
  });

  it("depois de um erro, 'vistos-carregando' tenta de novo e o erro some", () => {
    const erro = reducer(ESTADO_INICIAL, { tipo: "vistos-falhou", mensagem: "caiu" });
    expect(reducer(erro, { tipo: "vistos-carregando" }).vistos).toEqual({ situacao: "carregando" });
  });

  it("selecionar e limpar a seleção não mexem em modo nem em vistos", () => {
    const emVistos = reducer(ESTADO_INICIAL, { tipo: "trocar-modo", modo: "vistos" });
    for (const acao of [
      { tipo: "selecionar", codigo: "DK" },
      { tipo: "limpar-selecao" },
    ] as const) {
      const depois = reducer(emVistos, acao);
      expect(depois.modo).toBe("vistos");
      expect(depois.vistos).toEqual(emVistos.vistos);
    }
  });

  it("nada do modo é gravado no navegador", () => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    let estado = reducer(ESTADO_INICIAL, { tipo: "trocar-modo", modo: "vistos" });
    estado = reducer(estado, { tipo: "alternar-visto", chave: "isento" });
    estado = reducer(estado, { tipo: "vistos-carregando" });
    expect(estado.modo).toBe("vistos");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("estado: painel recolhível (FR-030)", () => {
  const aberto = {
    ...ESTADO_INICIAL,
    selecionado: "DK",
    postosExpandidos: [1, 2],
    grupoEmDestaque: "55.6761,12.5683",
    modo: "vistos" as const,
    niveisMarcados: ["nao_viajar" as const],
    vistosMarcados: ["isento" as const],
  };
  const recolhido = reducer(aberto, { tipo: "recolher-painel" });

  it("começa expandido", () => {
    expect(ESTADO_INICIAL.painelRecolhido).toBe(false);
  });

  it("recolher e expandir alternam só esse campo", () => {
    expect(recolhido).toEqual({ ...aberto, painelRecolhido: true });
    expect(reducer(recolhido, { tipo: "expandir-painel" })).toEqual({
      ...aberto,
      painelRecolhido: false,
    });
  });

  it("recolher de novo ou expandir já expandido não muda nada", () => {
    expect(reducer(recolhido, { tipo: "recolher-painel" })).toBe(recolhido);
    expect(reducer(aberto, { tipo: "expandir-painel" })).toBe(aberto);
  });

  it.each([
    { tipo: "selecionar", codigo: "PT" },
    { tipo: "tocar-icone", territorio: "DK", grupo: "g", ids: [1, 2] },
    { tipo: "expandir-posto", id: 1, grupo: "55.6761,12.5683" },
    { tipo: "limpar-selecao" },
  ] as const)("'$tipo' devolve o painel ao estado expandido", (acao) => {
    expect(reducer(recolhido, acao).painelRecolhido).toBe(false);
  });

  it.each([
    { tipo: "alternar-nivel", nivel: "evitar" },
    { tipo: "trocar-modo", modo: "alertas" },
    { tipo: "alternar-visto", chave: "visto_exigido" },
    { tipo: "marcar-todos-niveis" },
    { tipo: "vistos-carregando" },
  ] as const)("'$tipo' não altera o recolhimento", (acao) => {
    expect(reducer(recolhido, acao).painelRecolhido).toBe(true);
    expect(reducer(aberto, acao).painelRecolhido).toBe(false);
  });

  it("nada do recolhimento é gravado no navegador", () => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    const estado = reducer(recolhido, { tipo: "expandir-painel" });
    reducer(estado, { tipo: "recolher-painel" });
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});
