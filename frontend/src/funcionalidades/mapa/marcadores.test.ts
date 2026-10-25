import { describe, expect, it } from "vitest";
import type { Mapa, PostoNoMapa } from "../../servicos/api/cliente";
import { MAPA_COM_POSTOS } from "../../testes/dados-exemplo";
import {
  ZOOM_DOS_MARCADORES,
  agruparPostos,
  linhaAteOResponsavel,
  paisesSemPostoDesenhados,
  paisesSemPostoVisiveis,
  postosVisiveis,
  rotuloDoGrupo,
  rotuloDoPaisSemPosto,
  seloDoMarcador,
  varianteDoMarcador,
} from "./marcadores";

function posto(sobrescritas: Partial<PostoNoMapa> & Pick<PostoNoMapa, "id">): PostoNoMapa {
  return {
    territorio: "US",
    tipo: "Consulado",
    cidade: "Atlanta",
    latitude: 33.7,
    longitude: -84.4,
    grupo: "33.7,-84.4",
    ...sobrescritas,
  };
}

const ENTRADA = {
  zoom: 2,
  selecionado: null,
  gruposDoPainel: [] as readonly string[],
  grupoEmDestaque: null,
};

describe("ZOOM_DOS_MARCADORES", () => {
  it("os ícones aparecem a partir do zoom 3,5 (FR-017)", () => {
    expect(ZOOM_DOS_MARCADORES).toBe(3.5);
  });
});

describe("agruparPostos", () => {
  it("postos na mesma coordenada dividem um ícone, com os tipos do mais importante ao menos", () => {
    const grupos = agruparPostos([
      posto({ id: 90, tipo: "Consulado-Geral", grupo: "38.9,-77" }),
      posto({ id: 89, tipo: "Embaixada", grupo: "38.9,-77" }),
      posto({ id: 91, tipo: "Consulado", grupo: "33.7,-84.4" }),
    ]);
    expect(grupos).toHaveLength(2);
    expect(grupos[0]).toMatchObject({ grupo: "38.9,-77", tipos: ["Embaixada", "Consulado-Geral"] });
    expect(grupos[1]).toMatchObject({ grupo: "33.7,-84.4", tipos: ["Consulado"] });
  });

  it("guarda a coordenada e os países dos postos do grupo, sem repetir", () => {
    const [grupo] = agruparPostos(
      [
        posto({ id: 1, territorio: "IT", tipo: "Embaixada", latitude: 41.9, longitude: 12.5 }),
        posto({ id: 2, territorio: "VA", tipo: "Embaixada", latitude: 41.9, longitude: 12.5 }),
        posto({ id: 3, territorio: "IT", tipo: "Consulado", latitude: 41.9, longitude: 12.5 }),
      ].map((p) => ({ ...p, grupo: "41.9,12.5" })),
    );
    expect(grupo).toMatchObject({ latitude: 41.9, longitude: 12.5, territorios: ["IT", "VA"] });
    expect(grupo?.cidade).toBe("Atlanta"); // a cidade do primeiro posto do grupo
  });

  it("sem postos, sem ícones", () => {
    expect(agruparPostos([])).toEqual([]);
  });
});

describe("varianteDoMarcador e seloDoMarcador", () => {
  it.each([
    [["Embaixada"], "embaixada"],
    [["Embaixada", "Consulado-Geral"], "embaixada"],
    [["Consulado-Geral"], "consulado"],
    [["Consulado"], "consulado"],
    [["Vice-Consulado"], "consulado"],
    [["Escritório de Representação"], "escritorio"],
    [["Escritório Comercial"], "escritorio"],
    [["Escritório Comercial", "Consulado"], "consulado"],
  ] as const)("%j tem o ícone %s", (tipos, variante) => {
    expect(varianteDoMarcador(tipos)).toBe(variante);
  });

  it("ícone compartilhado por dois postos mostra o selo +1", () => {
    expect(seloDoMarcador(["Embaixada", "Consulado-Geral"])).toBe(1);
    expect(seloDoMarcador(["Embaixada"])).toBe(0);
    expect(seloDoMarcador(["Embaixada", "Consulado", "Consulado-Geral"])).toBe(2);
  });
});

describe("rótulos acessíveis", () => {
  it("o ícone de posto diz o tipo principal e a cidade", () => {
    expect(rotuloDoGrupo({ tipos: ["Consulado-Geral"], cidade: "Miami" })).toBe(
      "Consulado-Geral em Miami",
    );
  });

  it("o ícone compartilhado diz quantos postos mais há", () => {
    expect(rotuloDoGrupo({ tipos: ["Embaixada", "Consulado-Geral"], cidade: "Washington" })).toBe(
      "Embaixada em Washington e mais 1 posto",
    );
    expect(
      rotuloDoGrupo({ tipos: ["Embaixada", "Consulado", "Consulado-Geral"], cidade: "Roma" }),
    ).toBe("Embaixada em Roma e mais 2 postos");
  });

  it("o ícone de país sem posto diz o país", () => {
    expect(rotuloDoPaisSemPosto({ nome: "Porto Rico (Estados Unidos)" })).toBe(
      "Porto Rico (Estados Unidos): sem posto brasileiro no país",
    );
  });
});

describe("paisesSemPostoDesenhados", () => {
  it("liga cada país sem posto ao ponto do posto responsável", () => {
    const lista = paisesSemPostoDesenhados(MAPA_COM_POSTOS);
    const pr = lista.find((p) => p.territorio === "PR");
    expect(pr).toMatchObject({
      nome: "Porto Rico (Estados Unidos)",
      latitude: 18.2,
      longitude: -66.5,
      responsavel: { latitude: 25.76, longitude: -80.19, grupo: "25.76,-80.19" },
    });
  });

  it("sem posto indicado (Líbia), o responsável é nulo", () => {
    const lista = paisesSemPostoDesenhados(MAPA_COM_POSTOS);
    expect(lista.find((p) => p.territorio === "LY")?.responsavel).toBeNull();
  });
});

describe("linhaAteOResponsavel", () => {
  const lista = paisesSemPostoDesenhados(MAPA_COM_POSTOS);

  it("liga o ícone do país selecionado ao do posto responsável", () => {
    expect(linhaAteOResponsavel("PR", lista)).toEqual([
      [-66.5, 18.2],
      [-80.19, 25.76],
    ]);
  });

  it("não há linha sem seleção, para país com posto ou sem posto indicado", () => {
    expect(linhaAteOResponsavel(null, lista)).toBeNull();
    expect(linhaAteOResponsavel("US", lista)).toBeNull();
    expect(linhaAteOResponsavel("LY", lista)).toBeNull();
  });
});

describe("postosVisiveis", () => {
  const postos = agruparPostos(MAPA_COM_POSTOS.postos);
  const grupos = (entrada: Parameters<typeof postosVisiveis>[0]) =>
    postosVisiveis(entrada, postos, paisesSemPostoDesenhados(MAPA_COM_POSTOS)).map((p) => p.grupo);

  it("abaixo do zoom 3,5 nenhum ícone aparece", () => {
    expect(grupos({ ...ENTRADA, zoom: 3.49 })).toEqual([]);
  });

  it("a partir do zoom 3,5 todos aparecem", () => {
    expect(grupos({ ...ENTRADA, zoom: 3.5 })).toHaveLength(postos.length);
  });

  it("o grupo em destaque aparece em qualquer zoom (FR-018h)", () => {
    expect(grupos({ ...ENTRADA, grupoEmDestaque: "55.6761,12.5683" })).toEqual(["55.6761,12.5683"]);
  });

  it("os ícones dos postos do painel aberto aparecem em qualquer zoom", () => {
    expect(grupos({ ...ENTRADA, selecionado: "US", gruposDoPainel: ["38.9,-77"] })).toEqual([
      "38.9,-77",
    ]);
  });

  it("o posto responsável do país sem posto selecionado aparece em qualquer zoom (FR-018e)", () => {
    expect(grupos({ ...ENTRADA, selecionado: "PR" })).toEqual(["25.76,-80.19"]);
  });

  it("não repete o ícone que cai em mais de uma regra", () => {
    expect(
      grupos({
        zoom: 5,
        selecionado: "PR",
        gruposDoPainel: ["25.76,-80.19"],
        grupoEmDestaque: "25.76,-80.19",
      }).filter((g) => g === "25.76,-80.19"),
    ).toHaveLength(1);
  });
});

describe("paisesSemPostoVisiveis", () => {
  const lista = paisesSemPostoDesenhados(MAPA_COM_POSTOS);

  it("abaixo do zoom 3,5 só aparece o ícone do país sem posto selecionado", () => {
    expect(paisesSemPostoVisiveis({ ...ENTRADA, zoom: 2 }, lista)).toEqual([]);
    expect(
      paisesSemPostoVisiveis({ ...ENTRADA, zoom: 2, selecionado: "PR" }, lista).map(
        (p) => p.territorio,
      ),
    ).toEqual(["PR"]);
  });

  it("a partir do zoom 3,5 todos aparecem", () => {
    expect(paisesSemPostoVisiveis({ ...ENTRADA, zoom: 4 }, lista)).toHaveLength(lista.length);
  });
});

describe("os dados de exemplo de /mapa", () => {
  it("têm um grupo com dois postos e um país sem posto", () => {
    const mapa: Mapa = MAPA_COM_POSTOS;
    expect(mapa.postos.filter((p) => p.grupo === "38.9,-77")).toHaveLength(2);
    expect(mapa.paises_sem_posto.length).toBeGreaterThan(1);
  });
});
