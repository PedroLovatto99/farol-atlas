import { describe, expect, it } from "vitest";
import { rgbDeHex } from "../../compartilhado/contraste";
import { CORES_DE_VISTO, COR_DAS_LISTRAS } from "../../compartilhado/vistos";
import {
  LADO_DO_PADRAO,
  LARGURA_DA_LISTRA,
  PASSO_DA_LISTRA,
  amostraListrada,
  matrizDasListras,
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
