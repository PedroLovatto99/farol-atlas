/**
 * Padrão de listras do "Isento, entrada com RG" (FR-022a). A figura é uma matriz de pixels gerada
 * por função pura, sem canvas: o adaptador a registra no MapLibre com `map.addImage`, e a amostra
 * da legenda a reproduz em CSS com os mesmos números.
 */
import { rgbDeHex } from "../../compartilhado/contraste";
import { COR_DAS_LISTRAS, CORES_DE_VISTO } from "../../compartilhado/vistos";

export const NOME_DA_IMAGEM_DE_LISTRAS = "listras-rg";
export const LADO_DO_PADRAO = 16;
/** Listras diagonais (45°): o pixel (x, y) é de listra quando (x + y) mod PASSO < LARGURA. */
export const LARGURA_DA_LISTRA = 3;
export const PASSO_DA_LISTRA = 8;

export interface ImagemDoPadrao {
  width: number;
  height: number;
  /** RGBA, 4 bytes por pixel, linha a linha. */
  data: Uint8Array;
}

/** A imagem inclui a cor-base do "Isento", porque `fill-pattern` substitui o preenchimento. */
export function matrizDasListras(): ImagemDoPadrao {
  const listra = rgbDeHex(COR_DAS_LISTRAS);
  const base = rgbDeHex(CORES_DE_VISTO.isento);
  const data = new Uint8Array(LADO_DO_PADRAO * LADO_DO_PADRAO * 4);
  for (let y = 0; y < LADO_DO_PADRAO; y++) {
    for (let x = 0; x < LADO_DO_PADRAO; x++) {
      const cor = (x + y) % PASSO_DA_LISTRA < LARGURA_DA_LISTRA ? listra : base;
      const i = (y * LADO_DO_PADRAO + x) * 4;
      data[i] = cor[0];
      data[i + 1] = cor[1];
      data[i + 2] = cor[2];
      data[i + 3] = 255;
    }
  }
  return { width: LADO_DO_PADRAO, height: LADO_DO_PADRAO, data };
}

/**
 * A mesma figura em CSS: um ladrilho do tamanho do passo com um degradê a 135°, em que o pixel de
 * posição (x + y) ocupa (x + y) / (2 × passo) do degradê. Mesmas cores, largura, passo e emenda.
 */
export function amostraListrada(): { backgroundImage: string; backgroundSize: string } {
  const fim = (LARGURA_DA_LISTRA / (2 * PASSO_DA_LISTRA)) * 100;
  const meio = 50;
  const listra = COR_DAS_LISTRAS;
  const base = CORES_DE_VISTO.isento;
  return {
    backgroundImage:
      `linear-gradient(135deg, ${listra} 0%, ${listra} ${fim}%, ${base} ${fim}%, ${base} ${meio}%, ` +
      `${listra} ${meio}%, ${listra} ${meio + fim}%, ${base} ${meio + fim}%, ${base} 100%)`,
    backgroundSize: `${PASSO_DA_LISTRA}px ${PASSO_DA_LISTRA}px`,
  };
}
