import { describe, expect, it } from "vitest";
import type { SituacaoDeVisto } from "../servicos/api/cliente";
import {
  AVISO_DE_FONTE_NAO_OFICIAL,
  ORDEM_DE_EXIGENCIA,
  PERMANENCIA_DIVERGENTE,
  PERMANENCIA_VARIA_CONFORME_O_MOTIVO,
  ROTULOS_DE_VISTO,
  TEXTO_NAO_TRADUZIDO,
  TEXTO_TRADUCAO_AUTOMATICA,
  VARIA_CONFORME_O_MOTIVO,
} from "./vistos";

describe("rótulos das categorias de visto", () => {
  it("cada situação do contrato tem o rótulo em português", () => {
    const esperado: Record<SituacaoDeVisto, string> = {
      isento: "Isento de visto",
      visto_na_chegada: "Visto na chegada",
      autorizacao_eletronica: "Autorização ou visto eletrônico",
      visto_exigido: "Visto exigido",
      outra_situacao: "Outra situação",
      sem_informacao: "Sem informação de visto",
    };
    expect(ROTULOS_DE_VISTO).toEqual(esperado);
  });

  it("os rótulos são todos diferentes (a categoria nunca se confunde com outra)", () => {
    const rotulos = Object.values(ROTULOS_DE_VISTO);
    expect(new Set(rotulos).size).toBe(rotulos.length);
  });
});

describe("ordem de exigência (FR-007)", () => {
  it("vai da menos para a mais exigente e deixa 'Outra situação' e 'sem informação' de fora", () => {
    expect(ORDEM_DE_EXIGENCIA).toEqual([
      "isento",
      "visto_na_chegada",
      "autorizacao_eletronica",
      "visto_exigido",
    ]);
  });
});

describe("textos fixos", () => {
  it("o aviso diz que a fonte não é oficial e manda conferir com o consulado ou a embaixada", () => {
    expect(AVISO_DE_FONTE_NAO_OFICIAL).toMatch(/não oficial/i);
    expect(AVISO_DE_FONTE_NAO_OFICIAL).toContain("consulado ou embaixada");
  });

  it("a nota e as permanências que variam usam as frases da especificação", () => {
    expect(VARIA_CONFORME_O_MOTIVO).toBe("Varia conforme o motivo da viagem");
    expect(PERMANENCIA_VARIA_CONFORME_O_MOTIVO).toBe("Varia conforme o motivo (ver observações)");
    expect(PERMANENCIA_DIVERGENTE).toBe("Prazos divergentes na fonte (ver observações)");
  });

  it("marca a tradução como automática e o texto sem tradução como não traduzido", () => {
    expect(TEXTO_TRADUCAO_AUTOMATICA).toBe("tradução automática");
    expect(TEXTO_NAO_TRADUZIDO).toBe("não traduzido");
  });
});
