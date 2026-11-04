/**
 * Contorno dos países (camada `fronteiras`). No modo "Alertas" é a linha branca da 001; no modo
 * "Vistos" é escura (`#1F2A44`, opaca), para que o objeto gráfico se distinga do oceano e das cores
 * claras da paleta (WCAG 1.4.11, plan.md). Com o modo daltonismo, "Alertas" usa a mesma linha escura,
 * para "sem alerta" não se confundir com o oceano (FR-008a). Função pura: o adaptador só aplica o
 * resultado.
 */
import { COR_DO_CONTORNO_NO_MODO_VISTOS } from "../../compartilhado/vistos";
import type { ModoDoGlobo } from "./tipos";

export interface Contorno {
  cor: string;
  /** Em pixels. */
  largura: number;
}

export const CONTORNO_DO_MODO_ALERTAS: Contorno = { cor: "#ffffff", largura: 0.6 };
export const CONTORNO_DO_MODO_VISTOS: Contorno = {
  cor: COR_DO_CONTORNO_NO_MODO_VISTOS,
  largura: 0.6,
};

export function contornoDosPaises(modo: ModoDoGlobo, daltonismo = false): Contorno {
  return modo === "vistos" || daltonismo ? CONTORNO_DO_MODO_VISTOS : CONTORNO_DO_MODO_ALERTAS;
}

/** `null` devolve a camada à transição padrão do mapa; só o movimento reduzido a zera (research D9). */
export function transicaoDoContorno(
  reduzirMovimento: boolean,
): { duration: number; delay: number } | null {
  return reduzirMovimento ? { duration: 0, delay: 0 } : null;
}
