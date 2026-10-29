/**
 * Distância entre cores (CIEDE2000) e simulação de daltonismo, para conferir que as cores do modo
 * "Vistos" se distinguem entre si e das de alerta em visão normal e nas três formas de daltonismo
 * (protanopia, deuteranopia e tritanopia). Funções puras; o `Rgb` vem de `contraste.ts`.
 */
import type { Rgb } from "./contraste";

export type Lab = readonly [number, number, number];
export type TipoDeDaltonismo = "protanopia" | "deuteranopia" | "tritanopia";

/** sRGB (0 a 255) para o canal linear (0 a 1). */
function linearizar(canal: number): number {
  const c = canal / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

/** Canal linear (0 a 1) para sRGB (0 a 255). */
function gama(linear: number): number {
  const c = Math.min(1, Math.max(0, linear));
  return 255 * (c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055);
}

type Matriz = readonly [Rgb, Rgb, Rgb];

/** Matrizes de Machado, Oliveira e Fernandes (2009), severidade 1, aplicadas em RGB linear. */
const MATRIZES: Readonly<Record<TipoDeDaltonismo, Matriz>> = {
  protanopia: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deuteranopia: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881],
  ],
  tritanopia: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.3039],
  ],
};

/** Como alguém com `tipo` de daltonismo vê a cor (canais inteiros de 0 a 255). */
export function simularDaltonismo(rgb: Rgb, tipo: TipoDeDaltonismo): Rgb {
  const [r, g, b] = rgb.map(linearizar) as [number, number, number];
  const [sr, sg, sb] = MATRIZES[tipo].map((l) =>
    Math.round(gama(l[0] * r + l[1] * g + l[2] * b)),
  ) as [number, number, number];
  return [sr, sg, sb];
}

const BRANCO_D65 = [0.95047, 1, 1.08883] as const;

function f(t: number): number {
  return t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116;
}

/** sRGB para CIE Lab (iluminante D65). */
export function labDeRgb(rgb: Rgb): Lab {
  const [r, g, b] = rgb.map(linearizar) as [number, number, number];
  const x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / BRANCO_D65[0];
  const y = (0.2126729 * r + 0.7151522 * g + 0.072175 * b) / BRANCO_D65[1];
  const z = (0.0193339 * r + 0.119192 * g + 0.9503041 * b) / BRANCO_D65[2];
  const [fx, fy, fz] = [f(x), f(y), f(z)] as const;
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

const emRadianos = (graus: number) => (graus * Math.PI) / 180;

/** Ângulo de matiz em graus, de 0 a 360. */
function matiz(b: number, a: number): number {
  if (a === 0 && b === 0) return 0;
  const h = (Math.atan2(b, a) * 180) / Math.PI;
  return h >= 0 ? h : h + 360;
}

/** CIEDE2000 (Sharma, Wu e Dalal, 2005), com kL = kC = kH = 1. */
export function distanciaCiede2000(lab1: Lab, lab2: Lab): number {
  const [l1, a1, b1] = lab1;
  const [l2, a2, b2] = lab2;
  const cMedio = (Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2;
  const g = 0.5 * (1 - Math.sqrt(cMedio ** 7 / (cMedio ** 7 + 25 ** 7)));
  const a1p = (1 + g) * a1;
  const a2p = (1 + g) * a2;
  const c1p = Math.hypot(a1p, b1);
  const c2p = Math.hypot(a2p, b2);
  const h1p = matiz(b1, a1p);
  const h2p = matiz(b2, a2p);

  const dLp = l2 - l1;
  const dCp = c2p - c1p;
  let dhp = 0;
  if (c1p * c2p !== 0) {
    dhp = h2p - h1p;
    if (dhp > 180) dhp -= 360;
    else if (dhp < -180) dhp += 360;
  }
  const dHp = 2 * Math.sqrt(c1p * c2p) * Math.sin(emRadianos(dhp / 2));

  const lMedio = (l1 + l2) / 2;
  const cpMedio = (c1p + c2p) / 2;
  let hpMedio = h1p + h2p;
  if (c1p * c2p !== 0) {
    hpMedio =
      Math.abs(h1p - h2p) <= 180
        ? (h1p + h2p) / 2
        : (h1p + h2p + (h1p + h2p < 360 ? 360 : -360)) / 2;
  }

  const t =
    1 -
    0.17 * Math.cos(emRadianos(hpMedio - 30)) +
    0.24 * Math.cos(emRadianos(2 * hpMedio)) +
    0.32 * Math.cos(emRadianos(3 * hpMedio + 6)) -
    0.2 * Math.cos(emRadianos(4 * hpMedio - 63));
  const dTheta = 30 * Math.exp(-(((hpMedio - 275) / 25) ** 2));
  const rC = 2 * Math.sqrt(cpMedio ** 7 / (cpMedio ** 7 + 25 ** 7));
  const sL = 1 + (0.015 * (lMedio - 50) ** 2) / Math.sqrt(20 + (lMedio - 50) ** 2);
  const sC = 1 + 0.045 * cpMedio;
  const sH = 1 + 0.015 * cpMedio * t;
  const rT = -Math.sin(emRadianos(2 * dTheta)) * rC;

  const termoL = dLp / sL;
  const termoC = dCp / sC;
  const termoH = dHp / sH;
  return Math.sqrt(termoL ** 2 + termoC ** 2 + termoH ** 2 + rT * termoC * termoH);
}

/** CIEDE2000 entre duas cores sRGB. */
export function distanciaEntreCores(a: Rgb, b: Rgb): number {
  return distanciaCiede2000(labDeRgb(a), labDeRgb(b));
}
