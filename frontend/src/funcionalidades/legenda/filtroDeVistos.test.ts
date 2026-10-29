import { describe, expect, it } from "vitest";
import type { SituacaoNoGlobo } from "../../servicos/api/cliente";
import { TODAS_AS_CHAVES_DE_VISTO, type ChaveDeVisto } from "../../compartilhado/vistos";
import {
  alternarVisto,
  estadoDoIsento,
  nenhumVistoMarcado,
  territorioDeVistoEsmaecido,
} from "./filtroDeVistos";

const todas = [...TODAS_AS_CHAVES_DE_VISTO];
const sem = (...chaves: ChaveDeVisto[]) => todas.filter((c) => !chaves.includes(c));
const so = (...chaves: ChaveDeVisto[]) => chaves;

const SEM_RG = { situacao: "isento" as SituacaoNoGlobo, aceitaRg: false };
const COM_RG = { situacao: "isento" as SituacaoNoGlobo, aceitaRg: true };

describe("tabela de verdade do 'Isento' (isento × isento_rg)", () => {
  it.each<[string, ChaveDeVisto[], boolean, boolean]>([
    // marcadas, esmaecido do isento sem RG, esmaecido do isento com RG
    ["os dois marcados", so("isento", "isento_rg"), false, false],
    ["só o pai marcado", so("isento"), false, true],
    ["só o subitem marcado", so("isento_rg"), true, false],
    ["nenhum dos dois", so(), true, true],
  ])("%s", (_nome, marcadas, semRgEsmaecido, comRgEsmaecido) => {
    expect(territorioDeVistoEsmaecido(SEM_RG, marcadas)).toBe(semRgEsmaecido);
    expect(territorioDeVistoEsmaecido(COM_RG, marcadas)).toBe(comRgEsmaecido);
  });
});

describe("marcar e desmarcar com subitem", () => {
  it("desmarcar o pai desmarca também o subitem", () => {
    const depois = alternarVisto(todas, "isento");
    expect(depois).not.toContain("isento");
    expect(depois).not.toContain("isento_rg");
    expect(depois).toContain("visto_exigido");
  });

  it("marcar o pai marca também o subitem", () => {
    const depois = alternarVisto(sem("isento", "isento_rg"), "isento");
    expect(depois).toContain("isento");
    expect(depois).toContain("isento_rg");
  });

  it("desmarcar só o subitem deixa o pai em estado misto", () => {
    const depois = alternarVisto(todas, "isento_rg");
    expect(depois).toContain("isento");
    expect(depois).not.toContain("isento_rg");
    expect(estadoDoIsento(depois)).toBe("misto");
  });

  it("marcar só o subitem, com o pai desmarcado, mostra só os com RG (pai em estado misto)", () => {
    const depois = alternarVisto(sem("isento", "isento_rg"), "isento_rg");
    expect(depois).toEqual(expect.arrayContaining(["isento_rg"]));
    expect(depois).not.toContain("isento");
    expect(estadoDoIsento(depois)).toBe("misto");
    expect(territorioDeVistoEsmaecido(COM_RG, depois)).toBe(false);
    expect(territorioDeVistoEsmaecido(SEM_RG, depois)).toBe(true);
  });

  it("clicar no pai em estado misto marca os dois", () => {
    const depois = alternarVisto(so("isento"), "isento");
    expect(estadoDoIsento(depois)).toBe("marcado");
  });

  it("estado do pai: marcado, misto e desmarcado", () => {
    expect(estadoDoIsento(todas)).toBe("marcado");
    expect(estadoDoIsento(so("isento"))).toBe("misto");
    expect(estadoDoIsento(so("isento_rg"))).toBe("misto");
    expect(estadoDoIsento(so("visto_exigido"))).toBe("desmarcado");
  });

  it("as outras chaves alternam sozinhas", () => {
    const depois = alternarVisto(todas, "visto_exigido");
    expect(depois).not.toContain("visto_exigido");
    expect(depois).toContain("isento");
    expect(alternarVisto(depois, "visto_exigido")).toContain("visto_exigido");
  });

  it("não altera a lista de entrada", () => {
    const antes = [...todas];
    alternarVisto(todas, "isento");
    expect(todas).toEqual(antes);
  });
});

describe("esmaecer os demais territórios", () => {
  it.each<[SituacaoNoGlobo, ChaveDeVisto]>([
    ["visto_na_chegada", "visto_na_chegada"],
    ["autorizacao_eletronica", "autorizacao_eletronica"],
    ["visto_exigido", "visto_exigido"],
    ["outra_situacao", "outra_situacao"],
    ["sem_informacao", "sem_informacao"],
  ])("%s esmaece só quando a chave %s está desmarcada", (situacao, chave) => {
    const t = { situacao, aceitaRg: false };
    expect(territorioDeVistoEsmaecido(t, todas)).toBe(false);
    expect(territorioDeVistoEsmaecido(t, sem(chave))).toBe(true);
    expect(territorioDeVistoEsmaecido(t, sem(...todas.filter((c) => c !== chave)))).toBe(false);
  });

  it("o Brasil (não se aplica) nunca esmaece, porque não tem chave", () => {
    const brasil = { situacao: "nao_se_aplica" as SituacaoNoGlobo, aceitaRg: false };
    expect(territorioDeVistoEsmaecido(brasil, [])).toBe(false);
  });

  it("um território sem dado segue a chave 'sem informação', não a de nenhuma categoria", () => {
    const t = { situacao: "sem_informacao" as SituacaoNoGlobo, aceitaRg: false };
    expect(territorioDeVistoEsmaecido(t, sem("visto_exigido", "isento"))).toBe(false);
  });

  it("aceita_rg só conta para o 'Isento'", () => {
    const t = { situacao: "visto_exigido" as SituacaoNoGlobo, aceitaRg: true };
    expect(territorioDeVistoEsmaecido(t, sem("isento_rg"))).toBe(false);
  });
});

describe("todas desmarcadas", () => {
  it("nenhumVistoMarcado só é verdadeiro com a lista vazia", () => {
    expect(nenhumVistoMarcado([])).toBe(true);
    expect(nenhumVistoMarcado(so("sem_informacao"))).toBe(false);
  });
});
