/**
 * Planejamento da câmera: função pura, sem MapLibre. Transforma um pedido de câmera no que o
 * adaptador precisa executar. O adaptador só mede o que a função pede e a executa.
 */
import type { PedidoDeEnquadramento } from "./enquadramento";
import type { Margem, PedidoDeCamera } from "./tipos";

interface Ponto {
  latitude: number;
  longitude: number;
}

/** O que o adaptador mede no mapa para decidir se precisa mover. */
export interface ContextoDaCamera {
  /** Centro atual do mapa. */
  centro: Ponto;
  /** Posição do ponto pedido na tela, em pixels; nula se o mapa não conseguiu projetá-lo. */
  pontoNaTela: { x: number; y: number } | null;
  tamanho: { largura: number; altura: number };
}

export type PlanoDeCamera =
  | { tipo: "nenhum" }
  | { tipo: "mundo" }
  | PedidoDeEnquadramento
  /** Só desloca o centro até o ponto; o zoom nunca muda (FR-018c, FR-018h). */
  | ({ tipo: "centralizar"; margem: Margem } & Ponto);

const RAIO_DO_GLOBO_VISIVEL = 90;

function emRadianos(graus: number): number {
  return (graus * Math.PI) / 180;
}

/** Distância entre dois pontos da esfera, em graus (círculo máximo). */
export function distanciaAngular(a: Ponto, b: Ponto): number {
  const cos =
    Math.sin(emRadianos(a.latitude)) * Math.sin(emRadianos(b.latitude)) +
    Math.cos(emRadianos(a.latitude)) *
      Math.cos(emRadianos(b.latitude)) *
      Math.cos(emRadianos(a.longitude - b.longitude));
  return (Math.acos(Math.max(-1, Math.min(1, cos))) * 180) / Math.PI;
}

/**
 * O ponto está na área visível: no lado do globo voltado para a pessoa e dentro da tela, fora da
 * margem coberta pelo painel. Ponto do outro lado do globo nunca está visível, mesmo que a
 * projeção o jogue para dentro da tela.
 */
export function pontoVisivel(contexto: ContextoDaCamera, ponto: Ponto, margem: Margem): boolean {
  if (contexto.pontoNaTela === null) return false;
  if (distanciaAngular(contexto.centro, ponto) >= RAIO_DO_GLOBO_VISIVEL) return false;
  const { x, y } = contexto.pontoNaTela;
  const { largura, altura } = contexto.tamanho;
  return (
    x >= margem.esquerda &&
    x <= largura - margem.direita &&
    y >= margem.topo &&
    y <= altura - margem.baixo
  );
}

/**
 * `medir` só é chamada quando o pedido precisa saber como está o mapa (garantir-visivel).
 * "manter" (toque num ícone) nunca reenquadra.
 */
export function planejarCamera(
  pedido: PedidoDeCamera,
  medir: () => ContextoDaCamera,
): PlanoDeCamera {
  switch (pedido.tipo) {
    case "mundo":
    case "enquadrar":
      return pedido;
    case "centralizar":
      return pedido;
    case "manter":
      return { tipo: "nenhum" };
    case "garantir-visivel": {
      const ponto = { latitude: pedido.latitude, longitude: pedido.longitude };
      if (pontoVisivel(medir(), ponto, pedido.margem)) return { tipo: "nenhum" };
      return { tipo: "centralizar", ...ponto, margem: pedido.margem };
    }
  }
}
