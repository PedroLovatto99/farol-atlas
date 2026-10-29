/**
 * Contorno dos países (camada `fronteiras`). No modo "Alertas" é a linha branca da 001; no modo
 * "Vistos" é escura (`#1F2A44`, opaca), para que o objeto gráfico se distinga do oceano e das cores
 * claras da paleta (WCAG 1.4.11, plan.md). Função pura: o adaptador só aplica o resultado.
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

export function contornoDosPaises(modo: ModoDoGlobo): Contorno {
  return modo === "vistos" ? CONTORNO_DO_MODO_VISTOS : CONTORNO_DO_MODO_ALERTAS;
}
