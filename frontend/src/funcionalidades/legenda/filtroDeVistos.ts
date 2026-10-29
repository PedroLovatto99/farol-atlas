/** Filtro da legenda do modo "Vistos" (FR-022a, FR-024): funções puras, sem MapLibre. */
import type { ChaveDeVisto } from "../../compartilhado/vistos";
import type { SituacaoNoGlobo } from "../../servicos/api/cliente";

/** O que o filtro precisa saber de um território. */
export interface TerritorioParaFiltroDeVistos {
  situacao: SituacaoNoGlobo;
  aceitaRg: boolean;
}

/** A chave que governa o território; o Brasil (`nao_se_aplica`) não tem chave e nunca esmaece. */
function chaveDe({ situacao, aceitaRg }: TerritorioParaFiltroDeVistos): ChaveDeVisto | null {
  if (situacao === "nao_se_aplica") return null;
  if (situacao === "isento") return aceitaRg ? "isento_rg" : "isento";
  return situacao;
}

/**
 * Esmaece o território quando a chave dele está desmarcada. Um "Isento" com RG segue o subitem; um
 * "Isento" sem RG segue o item pai (tabela de verdade em `contracts/mapa-props-vistos.md`).
 */
export function territorioDeVistoEsmaecido(
  territorio: TerritorioParaFiltroDeVistos,
  marcadas: readonly ChaveDeVisto[],
): boolean {
  const chave = chaveDe(territorio);
  return chave !== null && !marcadas.includes(chave);
}

export type EstadoDoIsento = "marcado" | "misto" | "desmarcado";

/** O item pai fica misto quando só um dos dois (ele ou o subitem) está marcado (`aria-checked="mixed"`). */
export function estadoDoIsento(marcadas: readonly ChaveDeVisto[]): EstadoDoIsento {
  const pai = marcadas.includes("isento");
  const subitem = marcadas.includes("isento_rg");
  if (pai && subitem) return "marcado";
  return pai || subitem ? "misto" : "desmarcado";
}

/**
 * Marca ou desmarca uma chave. O item pai "Isento" leva o subitem junto: desmarcado ou misto vira
 * marcado nos dois; marcado vira desmarcado nos dois. O subitem alterna sozinho.
 */
export function alternarVisto(
  marcadas: readonly ChaveDeVisto[],
  chave: ChaveDeVisto,
): ChaveDeVisto[] {
  if (chave === "isento") {
    const semOsDois = marcadas.filter((c) => c !== "isento" && c !== "isento_rg");
    return estadoDoIsento(marcadas) === "marcado"
      ? semOsDois
      : [...semOsDois, "isento", "isento_rg"];
  }
  return marcadas.includes(chave) ? marcadas.filter((c) => c !== chave) : [...marcadas, chave];
}

export function nenhumVistoMarcado(marcadas: readonly ChaveDeVisto[]): boolean {
  return marcadas.length === 0;
}
