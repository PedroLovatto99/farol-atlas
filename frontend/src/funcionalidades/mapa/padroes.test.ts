import { describe, expect, it } from "vitest";
import { rgbDeHex } from "../../compartilhado/contraste";
import { CORES_DE_VISTO, COR_DAS_LISTRAS } from "../../compartilhado/vistos";
import { COR_DAS_MARCAS, paletaDe } from "./cor";
import {
  IMAGENS_DOS_PADROES,
  LADO_DO_PADRAO,
  LARGURA_DA_LISTRA,
  PASSO_DA_LISTRA,
  amostraDaBorda,
  amostraDoPadrao,
  amostraListrada,
  matrizDaHachura,
  matrizDasListras,
  matrizDosPontos,
  nomeDaImagem,
} from "./padroes";

function pixel(dados: Uint8Array, x: number, y: number): number[] {
  const i = (y * LADO_DO_PADRAO + x) * 4;
  return [dados[i]!, dados[i + 1]!, dados[i + 2]!, dados[i + 3]!];
}

describe("matriz das listras do 'Isento, entrada com RG'", () => {
  const imagem = matrizDasListras();

  it("é uma imagem RGBA de 16×16", () => {
    expect(imagem.width).toBe(16);
    expect(imagem.height).toBe(16);
    expect(imagem.data).toHaveLength(16 * 16 * 4);
  });

  it("é determinística", () => {
    expect(Array.from(matrizDasListras().data)).toEqual(Array.from(imagem.data));
  });

  it("tem listras de 3 px a cada 8 px, na diagonal de 45°", () => {
    expect(LARGURA_DA_LISTRA).toBe(3);
    expect(PASSO_DA_LISTRA).toBe(8);
    const listra = [...rgbDeHex(COR_DAS_LISTRAS), 255];
    const base = [...rgbDeHex(CORES_DE_VISTO.isento), 255];
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const emListra = (x + y) % PASSO_DA_LISTRA < LARGURA_DA_LISTRA;
        expect(pixel(imagem.data, x, y), `(${x},${y})`).toEqual(emListra ? listra : base);
      }
    }
  });

  it("é opaca, com a base do 'Isento' incluída (fill-pattern substitui o preenchimento)", () => {
    for (let i = 3; i < imagem.data.length; i += 4) expect(imagem.data[i]).toBe(255);
  });

  it("o desenho se repete sem emenda: a diagonal continua de uma borda à oposta", () => {
    for (let y = 0; y < 16; y++) {
      expect(pixel(imagem.data, 0, y)).toEqual(pixel(imagem.data, 8, y));
      expect(pixel(imagem.data, y, 0)).toEqual(pixel(imagem.data, y, 8));
    }
  });
});

describe("amostra da legenda", () => {
  // Um ladrilho de 8×8 px com um degradê a 135° reproduz (x + y) % 8 < 3 da imagem: as listras
  // seguem a mesma diagonal, com a mesma largura e o mesmo passo, e a mesma emenda.
  const { backgroundImage, backgroundSize } = amostraListrada();

  it("usa as mesmas cores da imagem", () => {
    expect(backgroundImage.toLowerCase()).toContain(COR_DAS_LISTRAS.toLowerCase());
    expect(backgroundImage.toLowerCase()).toContain(CORES_DE_VISTO.isento.toLowerCase());
  });

  it("usa os mesmos números da imagem: ladrilho do passo e paradas da largura da listra", () => {
    expect(backgroundSize).toBe(`${PASSO_DA_LISTRA}px ${PASSO_DA_LISTRA}px`);
    expect(backgroundImage).toContain("linear-gradient(135deg");
    const fim = (LARGURA_DA_LISTRA / (2 * PASSO_DA_LISTRA)) * 100; // 18,75%
    const inicio = 50;
    expect(backgroundImage).toContain(`${fim}%`);
    expect(backgroundImage).toContain(`${inicio + fim}%`);
  });
});

describe("listras do modo ligado", () => {
  const imagem = matrizDasListras(true);
  const listra = [...rgbDeHex("#0E2A20"), 255];
  const base = [...rgbDeHex("#FEDD50"), 255];

  it("sem argumento, a matriz continua a de hoje", () => {
    expect(Array.from(matrizDasListras().data)).toEqual(Array.from(matrizDasListras(false).data));
    expect(pixel(matrizDasListras().data, 0, 0)).toEqual([...rgbDeHex(COR_DAS_LISTRAS), 255]);
  });

  it("tem o mesmo desenho, com listras #0E2A20 e base #FEDD50 opaca", () => {
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const emListra = (x + y) % PASSO_DA_LISTRA < LARGURA_DA_LISTRA;
        expect(pixel(imagem.data, x, y), `(${x},${y})`).toEqual(emListra ? listra : base);
      }
    }
  });

  it("a amostra usa a cor nova; sem argumento, a de hoje", () => {
    expect(amostraListrada(true).backgroundImage).toContain("#0E2A20");
    expect(amostraListrada().backgroundImage).toContain(COR_DAS_LISTRAS);
    expect(amostraListrada().backgroundImage).not.toContain("#0E2A20");
  });
});

describe.each([
  {
    nome: "hachura",
    imagem: matrizDaHachura(),
    emMarca: (x: number, y: number) => (x + y) % 8 < 2 || (x - y + 16) % 8 < 2,
    cobertura: 0.438,
  },
  {
    nome: "pontos",
    imagem: matrizDosPontos(),
    emMarca: (x: number, y: number) => x % 8 < 3 && y % 8 < 3,
    cobertura: 0.141,
  },
])("padrão de $nome", ({ imagem, emMarca, cobertura }) => {
  const marca = [...rgbDeHex("#18142C"), 255];

  it("é um ladrilho de 16×16 com marcas #18142C e fundo transparente, pelas regras do contrato", () => {
    expect(imagem.width).toBe(16);
    expect(imagem.height).toBe(16);
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        expect(pixel(imagem.data, x, y), `(${x},${y})`).toEqual(
          emMarca(x, y) ? marca : [0, 0, 0, 0],
        );
      }
    }
  });

  it("tem a cobertura do contrato", () => {
    let marcados = 0;
    for (let i = 3; i < imagem.data.length; i += 4) if (imagem.data[i] === 255) marcados++;
    expect(marcados / 256).toBeCloseTo(cobertura, 2);
  });
});

describe("nomes das imagens", () => {
  it("seguem a tabela do contrato", () => {
    expect(nomeDaImagem("rg", false)).toBe("listras-rg");
    expect(nomeDaImagem("rg", true)).toBe("listras-rg-daltonismo");
    expect(nomeDaImagem("nao_viajar", true)).toBe("hachura-nao-viaje");
    expect(nomeDaImagem("evitar", true)).toBe("pontos-evite");
  });

  it("a tabela do mapa tem uma matriz para cada nome", () => {
    expect(Object.keys(IMAGENS_DOS_PADROES).sort()).toEqual([
      "hachura-nao-viaje",
      "listras-rg",
      "listras-rg-daltonismo",
      "pontos-evite",
    ]);
    expect(Array.from(IMAGENS_DOS_PADROES["listras-rg"]!().data)).toEqual(
      Array.from(matrizDasListras().data),
    );
    expect(Array.from(IMAGENS_DOS_PADROES["hachura-nao-viaje"]!().data)).toEqual(
      Array.from(matrizDaHachura().data),
    );
  });
});

/** O SVG de dentro de um `url("data:image/svg+xml,...")`. */
function svgDe(backgroundImage: string): string {
  const inicio = 'url("data:image/svg+xml,';
  expect(backgroundImage.startsWith(inicio)).toBe(true);
  return decodeURIComponent(backgroundImage.slice(inicio.length, -2));
}

describe("amostras de hachura e pontos (research D8)", () => {
  /** Os pixels marcados do SVG, como "x,y". */
  const marcados = (svg: string) =>
    [...svg.matchAll(/<rect x="(\d+)" y="(\d+)"/g)].map((m) => `${m[1]},${m[2]}`).sort();

  /** Os pixels marcados do canto 8×8 da matriz do mapa: o ladrilho da amostra é o mesmo desenho. */
  function marcadosDaMatriz(imagem: ReturnType<typeof matrizDaHachura>): string[] {
    const lista: string[] = [];
    for (let y = 0; y < 8; y++) {
      for (let x = 0; x < 8; x++) if (pixel(imagem.data, x, y)[3] === 255) lista.push(`${x},${y}`);
    }
    return lista.sort();
  }

  it.each([
    ["nao_viajar", matrizDaHachura(), 28],
    ["evitar", matrizDosPontos(), 9],
  ] as const)("%s: ladrilho 8×8 com os pixels da matriz do mapa", (padrao, matriz, quantos) => {
    const { backgroundImage, backgroundSize } = amostraDoPadrao(padrao);
    const svg = svgDe(backgroundImage);
    expect(backgroundSize).toBe("8px 8px");
    expect(svg).toContain('width="8"');
    expect(svg).toContain('height="8"');
    expect(svg).toContain(`fill="${COR_DAS_MARCAS}"`);
    expect(marcados(svg)).toHaveLength(quantos);
    expect(marcados(svg)).toEqual(marcadosDaMatriz(matriz));
  });
});

describe("amostra da borda do modo ligado (research D8)", () => {
  const amostra = amostraDaBorda();
  const svg = svgDe(amostra.backgroundImage);
  const { bordas } = paletaDe(true);

  it("mede 30×12", () => {
    expect(amostra.width).toBe(30);
    expect(amostra.height).toBe(12);
    expect(svg).toContain('width="30"');
    expect(svg).toContain('height="12"');
  });

  it("tem a linha contínua em cima e a tracejada, com os números do mapa, embaixo", () => {
    const linhas = [...svg.matchAll(/<line [^>]*>/g)].map((m) => m[0]);
    expect(linhas).toHaveLength(2);
    expect(linhas[0]).toContain(`stroke="${bordas.nao_viajar}"`);
    expect(linhas[0]).not.toContain("stroke-dasharray");
    expect(linhas[1]).toContain(`stroke="${bordas.evitar}"`);
    expect(linhas[1]).toContain('stroke-dasharray="7.5 5"');
    expect(linhas[0]).toContain('stroke-width="2.5"');
    expect(linhas[1]).toContain('stroke-width="2.5"');
    const altura = (linha: string | undefined) => Number(/ y1="([\d.]+)"/.exec(linha ?? "")?.[1]);
    expect(altura(linhas[0])).toBeLessThan(altura(linhas[1]));
  });
});
