/** Contraste de cores pela fórmula do WCAG 2.x (AA: 4,5:1 para texto normal, 3:1 para texto grande e componentes). */

export type Rgb = readonly [number, number, number];

export function rgbDeHex(hex: string): Rgb {
  const limpo = hex.replace("#", "");
  const inteiro = parseInt(limpo.length === 3 ? [...limpo].map((c) => c + c).join("") : limpo, 16);
  return [(inteiro >> 16) & 255, (inteiro >> 8) & 255, inteiro & 255];
}

/** Cor com opacidade `alfa` por cima de `fundo` (o que o olho vê). */
export function sobrepor(frente: Rgb, alfa: number, fundo: Rgb): Rgb {
  return [0, 1, 2].map((i) =>
    Math.round(frente[i]! * alfa + fundo[i]! * (1 - alfa)),
  ) as unknown as Rgb;
}

function luminancia([r, g, b]: Rgb): number {
  const [lr, lg, lb] = [r, g, b].map((canal) => {
    const c = canal / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

export function contraste(a: Rgb, b: Rgb): number {
  const [mais, menos] = [luminancia(a), luminancia(b)].sort((x, y) => y - x) as [number, number];
  return (mais + 0.05) / (menos + 0.05);
}
