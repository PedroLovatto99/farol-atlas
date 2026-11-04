/**
 * Padrões do mapa: as listras do "Isento, entrada com RG" (FR-022a) e, no modo daltonismo, a hachura
 * de "não viaje" e os pontos de "evite" (FR-009). Cada figura é uma matriz de pixels gerada por
 * função pura, sem canvas: o adaptador a registra no MapLibre com `map.addImage`, e a amostra da
 * legenda a reproduz com os mesmos números.
 */
import { rgbDeHex, type Rgb } from "../../compartilhado/contraste";
import { COR_DAS_MARCAS, paletaDe } from "./cor";
import type { BordaRegional, PadraoDoPreenchimento } from "./tipos";

export const NOME_DA_IMAGEM_DE_LISTRAS = "listras-rg";
export const LADO_DO_PADRAO = 16;
/** Listras diagonais (45°): o pixel (x, y) é de listra quando (x + y) mod PASSO < LARGURA. */
export const LARGURA_DA_LISTRA = 3;
export const PASSO_DA_LISTRA = 8;
/** Em pixels. O tracejado do MapLibre é medido em larguras de linha. */
export const LARGURA_DA_BORDA_REGIONAL = 2.5;
export const TRACEJADO_DA_BORDA_REGIONAL: [number, number] = [3, 2];

/** Os padrões de alerta: um desenho serve ao mapa e à amostra da legenda (research D8). */
const DESENHOS: Readonly<Record<BordaRegional, (x: number, y: number) => boolean>> = {
  nao_viajar: (x, y) => (x + y) % 8 < 2 || (x - y + 16) % 8 < 2,
  evitar: (x, y) => x % 8 < 3 && y % 8 < 3,
};

export interface ImagemDoPadrao {
  width: number;
  height: number;
  /** RGBA, 4 bytes por pixel, linha a linha. */
  data: Uint8Array;
}

/** `corDoPixel` nulo deixa o pixel transparente. */
function desenharMatriz(corDoPixel: (x: number, y: number) => Rgb | null): ImagemDoPadrao {
  const data = new Uint8Array(LADO_DO_PADRAO * LADO_DO_PADRAO * 4);
  for (let y = 0; y < LADO_DO_PADRAO; y++) {
    for (let x = 0; x < LADO_DO_PADRAO; x++) {
      const cor = corDoPixel(x, y);
      if (cor === null) continue;
      const i = (y * LADO_DO_PADRAO + x) * 4;
      data[i] = cor[0];
      data[i + 1] = cor[1];
      data[i + 2] = cor[2];
      data[i + 3] = 255;
    }
  }
  return { width: LADO_DO_PADRAO, height: LADO_DO_PADRAO, data };
}

/** A imagem inclui a cor-base do "Isento", porque `fill-pattern` substitui o preenchimento. */
export function matrizDasListras(daltonismo = false): ImagemDoPadrao {
  const paleta = paletaDe(daltonismo);
  const listra = rgbDeHex(paleta.listras);
  const base = rgbDeHex(paleta.vistos.isento);
  return desenharMatriz((x, y) => ((x + y) % PASSO_DA_LISTRA < LARGURA_DA_LISTRA ? listra : base));
}

/**
 * Só as marcas, com fundo transparente: a cor de base vem da camada `paises`, e o país filtrado
 * esmaece por igual (research D5).
 */
function matrizDeMarcas(desenho: (x: number, y: number) => boolean): ImagemDoPadrao {
  const marca = rgbDeHex(COR_DAS_MARCAS);
  return desenharMatriz((x, y) => (desenho(x, y) ? marca : null));
}

export const matrizDaHachura = () => matrizDeMarcas(DESENHOS.nao_viajar);
export const matrizDosPontos = () => matrizDeMarcas(DESENHOS.evitar);

/** As imagens que o mapa registra sob demanda, pelo nome gravado em cada feição. */
export const IMAGENS_DOS_PADROES: Readonly<Record<string, () => ImagemDoPadrao>> = {
  [NOME_DA_IMAGEM_DE_LISTRAS]: () => matrizDasListras(),
  "listras-rg-daltonismo": () => matrizDasListras(true),
  "hachura-nao-viaje": matrizDaHachura,
  "pontos-evite": matrizDosPontos,
};

export function nomeDaImagem(padrao: PadraoDoPreenchimento, daltonismo: boolean): string {
  if (padrao === "nao_viajar") return "hachura-nao-viaje";
  if (padrao === "evitar") return "pontos-evite";
  return daltonismo ? "listras-rg-daltonismo" : NOME_DA_IMAGEM_DE_LISTRAS;
}

/**
 * A mesma figura em CSS: um ladrilho do tamanho do passo com um degradê a 135°, em que o pixel de
 * posição (x + y) ocupa (x + y) / (2 × passo) do degradê. Mesmas cores, largura, passo e emenda.
 */
export function amostraListrada(daltonismo = false): {
  backgroundImage: string;
  backgroundSize: string;
} {
  const fim = (LARGURA_DA_LISTRA / (2 * PASSO_DA_LISTRA)) * 100;
  const meio = 50;
  const paleta = paletaDe(daltonismo);
  const listra = paleta.listras;
  const base = paleta.vistos.isento;
  return {
    backgroundImage:
      `linear-gradient(135deg, ${listra} 0%, ${listra} ${fim}%, ${base} ${fim}%, ${base} ${meio}%, ` +
      `${listra} ${meio}%, ${listra} ${meio + fim}%, ${base} ${meio + fim}%, ${base} 100%)`,
    backgroundSize: `${PASSO_DA_LISTRA}px ${PASSO_DA_LISTRA}px`,
  };
}

const urlDeSvg = (svg: string) => `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;

/** A amostra do padrão de um nível: o desenho do mapa, em ladrilho de 8×8, sem a cor de base. */
export function amostraDoPadrao(nivel: BordaRegional): {
  backgroundImage: string;
  backgroundSize: string;
} {
  let marcas = "";
  for (let y = 0; y < PASSO_DA_LISTRA; y++) {
    for (let x = 0; x < PASSO_DA_LISTRA; x++) {
      if (DESENHOS[nivel](x, y)) marcas += `<rect x="${x}" y="${y}" width="1" height="1"/>`;
    }
  }
  const lado = PASSO_DA_LISTRA;
  return {
    backgroundImage: urlDeSvg(
      `<svg xmlns="http://www.w3.org/2000/svg" width="${lado}" height="${lado}" ` +
        `fill="${COR_DAS_MARCAS}" shape-rendering="crispEdges">${marcas}</svg>`,
    ),
    backgroundSize: `${lado}px ${lado}px`,
  };
}

/** A amostra das bordas regionais do modo ligado: contínua em cima, tracejada embaixo, como no mapa. */
export function amostraDaBorda(): { backgroundImage: string; width: number; height: number } {
  const { bordas } = paletaDe(true);
  const [width, height] = [30, 12];
  const traco = TRACEJADO_DA_BORDA_REGIONAL.map((n) => n * LARGURA_DA_BORDA_REGIONAL).join(" ");
  const linha = (y: number, cor: string, extra = "") =>
    `<line x1="0" y1="${y}" x2="${width}" y2="${y}" stroke="${cor}" ` +
    `stroke-width="${LARGURA_DA_BORDA_REGIONAL}"${extra}/>`;
  return {
    backgroundImage: urlDeSvg(
      `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">` +
        linha(3, bordas.nao_viajar) +
        linha(9, bordas.evitar, ` stroke-dasharray="${traco}"`) +
        "</svg>",
    ),
    width,
    height,
  };
}
