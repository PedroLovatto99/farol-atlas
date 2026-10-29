import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { SituacaoDeVisto } from "../servicos/api/cliente";
import { contraste, rgbDeHex } from "./contraste";
import { distanciaEntreCores, simularDaltonismo, type TipoDeDaltonismo } from "./distanciaDeCor";
import { NIVEIS } from "./niveis";
import {
  AVISO_DE_FONTE_NAO_OFICIAL,
  CHAVES_DA_LEGENDA_DE_VISTOS,
  COR_DA_BORDA_DA_AMOSTRA,
  COR_DAS_LISTRAS,
  COR_DO_BRASIL_NO_MODO_VISTOS,
  COR_DO_CONTORNO_NO_MODO_VISTOS,
  COR_DO_OCEANO,
  CORES_DE_VISTO,
  ROTULOS_DA_LEGENDA_DE_VISTOS,
  TODAS_AS_CHAVES_DE_VISTO,
  type ChaveDeVisto,
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

const tema = readFileSync(resolve(process.cwd(), "src/compartilhado/tema.css"), "utf-8");

describe("paleta do modo 'Vistos' (plan.md)", () => {
  it("tem as cores aprovadas no plano", () => {
    expect(CORES_DE_VISTO).toEqual({
      isento: "#FEDD50",
      visto_na_chegada: "#D17DA4",
      autorizacao_eletronica: "#8F5FCC",
      visto_exigido: "#3B1C6B",
      outra_situacao: "#948878",
      sem_informacao: "#BEBAB1",
    });
    expect(COR_DO_BRASIL_NO_MODO_VISTOS).toBe("#F1EFE8");
    expect(COR_DAS_LISTRAS).toBe("#1F2A44");
    expect(COR_DA_BORDA_DA_AMOSTRA).toBe("#5F5E5A");
    expect(COR_DO_OCEANO).toBe("#DCE8F2");
  });

  it("as cores do código são as dos tokens --color-visto-* de tema.css", () => {
    const tokens: Record<string, string> = {
      "--color-visto-isento": CORES_DE_VISTO.isento,
      "--color-visto-listras": COR_DAS_LISTRAS,
      "--color-visto-na-chegada": CORES_DE_VISTO.visto_na_chegada,
      "--color-visto-autorizacao-eletronica": CORES_DE_VISTO.autorizacao_eletronica,
      "--color-visto-exigido": CORES_DE_VISTO.visto_exigido,
      "--color-visto-outra-situacao": CORES_DE_VISTO.outra_situacao,
      "--color-visto-sem-informacao": CORES_DE_VISTO.sem_informacao,
      "--color-visto-brasil": COR_DO_BRASIL_NO_MODO_VISTOS,
      "--color-visto-borda-da-amostra": COR_DA_BORDA_DA_AMOSTRA,
      "--color-visto-contorno": COR_DO_CONTORNO_NO_MODO_VISTOS,
    };
    for (const [token, cor] of Object.entries(tokens)) {
      const encontrado = new RegExp(`${token}:\\s*(#[0-9a-fA-F]{6})`).exec(tema);
      expect(encontrado, `token ${token} em tema.css`).not.toBeNull();
      expect(encontrado?.[1]?.toLowerCase()).toBe(cor.toLowerCase());
    }
  });

  it("o neutro do Brasil é o neutro que já existe (--color-area-neutra)", () => {
    const encontrado = /--color-area-neutra:\s*(#[0-9a-fA-F]{6})/.exec(tema);
    expect(encontrado?.[1]?.toLowerCase()).toBe(COR_DO_BRASIL_NO_MODO_VISTOS.toLowerCase());
  });

  it("o oceano é o do mapa (--color-oceano)", () => {
    const encontrado = /--color-oceano:\s*(#[0-9a-fA-F]{6})/.exec(tema);
    expect(encontrado?.[1]?.toLowerCase()).toBe(COR_DO_OCEANO.toLowerCase());
  });
});

describe("contraste (WCAG 2.x)", () => {
  it("as listras sobre a base do 'Isento' têm contraste de pelo menos 3 (WCAG 1.4.11)", () => {
    expect(
      contraste(rgbDeHex(COR_DAS_LISTRAS), rgbDeHex(CORES_DE_VISTO.isento)),
    ).toBeGreaterThanOrEqual(3);
  });

  it("a borda das amostras da legenda tem contraste de pelo menos 3 contra o branco (WCAG 1.4.11)", () => {
    expect(contraste(rgbDeHex(COR_DA_BORDA_DA_AMOSTRA), [255, 255, 255])).toBeGreaterThanOrEqual(3);
  });

  it("'sem informação' é mais escuro que o 'não verificado' dos alertas", () => {
    const luz = (hex: string) => {
      const [r, g, b] = rgbDeHex(hex);
      return (r + g + b) / 3;
    };
    expect(luz(CORES_DE_VISTO.sem_informacao)).toBeLessThan(luz(NIVEIS.nao_verificado.cor));
    expect(CORES_DE_VISTO.sem_informacao.toLowerCase()).not.toBe(
      NIVEIS.nao_verificado.cor.toLowerCase(),
    );
  });
});

describe("distância de cor (CIEDE2000), em visão normal e nas três simulações", () => {
  const LIMITE = 12;
  /**
   * Limite dos pares que nunca aparecem juntos no globo (um é do modo Alertas, o outro do modo
   * Vistos). O amarelo do "Isento" não chega a 12 contra o âmbar de "evite" nem, na protanopia, contra
   * o verde de "sem alerta", e o "sem informação" é o mesmo conceito do "não verificado" em outro tom.
   */
  const LIMITE_ENTRE_MODOS = 5.5;
  const DE_VISTO = Object.entries(CORES_DE_VISTO).map(([nome, cor]) => ({
    nome: `visto:${nome}`,
    cor,
  }));
  const ALERTAS = Object.entries(NIVEIS).map(([nome, n]) => ({
    nome: `alerta:${nome}`,
    cor: n.cor,
  }));
  const NO_MESMO_MAPA = [
    { nome: "Brasil", cor: COR_DO_BRASIL_NO_MODO_VISTOS },
    { nome: "oceano", cor: COR_DO_OCEANO },
  ];

  const VISOES: (TipoDeDaltonismo | "normal")[] = [
    "normal",
    "protanopia",
    "deuteranopia",
    "tritanopia",
  ];
  const ver = (hex: string, visao: TipoDeDaltonismo | "normal") => {
    const rgb = rgbDeHex(hex);
    return visao === "normal" ? rgb : simularDaltonismo(rgb, visao);
  };
  const distancias = (
    pares: readonly (readonly [{ nome: string; cor: string }, { nome: string; cor: string }])[],
    visao: TipoDeDaltonismo | "normal",
    limite: number,
  ) =>
    pares
      .map(([a, b]) => ({
        par: `${a.nome} × ${b.nome}`,
        distancia: distanciaEntreCores(ver(a.cor, visao), ver(b.cor, visao)),
      }))
      .filter((p) => p.distancia < limite);

  /** Pares que estão juntos no mesmo globo: entre as cores de visto, e delas com o Brasil e o oceano. */
  const JUNTOS = DE_VISTO.flatMap((a, i) => [
    ...DE_VISTO.slice(i + 1).map((b) => [a, b] as const),
    ...NO_MESMO_MAPA.map((b) => [a, b] as const),
  ]);

  const ENTRE_MODOS = DE_VISTO.flatMap((a) => ALERTAS.map((b) => [a, b] as const));
  const NAO_CHEGAM_A_12 = new Set([
    "visto:isento × alerta:evitar",
    "visto:isento × alerta:sem_alerta",
  ]);
  const SEM_INFORMACAO_X_NAO_VERIFICADO = "visto:sem_informacao × alerta:nao_verificado";

  it.each(VISOES)(
    "visão %s: as cores do mesmo globo ficam a pelo menos 12 uma da outra",
    (visao) => {
      expect(distancias(JUNTOS, visao, LIMITE)).toEqual([]);
    },
  );

  it.each(VISOES)(
    "visão %s: as cores de visto contra as de alerta ficam a 12, salvo as exceções registradas",
    (visao) => {
      const abaixo = distancias(ENTRE_MODOS, visao, LIMITE).map((p) => p.par);
      const inesperadas = abaixo.filter(
        (par) => !NAO_CHEGAM_A_12.has(par) && par !== SEM_INFORMACAO_X_NAO_VERIFICADO,
      );
      expect(inesperadas).toEqual([]);
    },
  );

  it.each(VISOES)("visão %s: nem as exceções (modos diferentes) caem abaixo de %s", (visao) => {
    expect(distancias(ENTRE_MODOS, visao, LIMITE_ENTRE_MODOS)).toEqual([]);
  });
});

describe("chaves da legenda", () => {
  it("são sete, na ordem de exibição, com o subitem logo depois do pai", () => {
    const esperado: ChaveDeVisto[] = [
      "isento",
      "isento_rg",
      "visto_na_chegada",
      "autorizacao_eletronica",
      "visto_exigido",
      "outra_situacao",
      "sem_informacao",
    ];
    expect([...CHAVES_DA_LEGENDA_DE_VISTOS]).toEqual(esperado);
    expect([...TODAS_AS_CHAVES_DE_VISTO].sort()).toEqual([...esperado].sort());
  });

  it("cada chave tem o rótulo da legenda em texto", () => {
    expect(ROTULOS_DA_LEGENDA_DE_VISTOS).toEqual({
      isento: "Isento de visto",
      isento_rg: "Isento, entrada com RG",
      visto_na_chegada: "Visto na chegada",
      autorizacao_eletronica: "Autorização ou visto eletrônico",
      visto_exigido: "Visto exigido",
      outra_situacao: "Outra situação",
      sem_informacao: "Sem informação de visto",
    });
  });
});
