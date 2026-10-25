/** Filtro da legenda por nível (FR-024 a FR-027): funções puras, sem MapLibre. */
import type { NivelId } from "../../compartilhado/niveis";
import type { Regiao } from "../../servicos/api/cliente";

/** O que o filtro precisa saber de um território; `nivel` nulo é área neutra. */
export interface TerritorioParaFiltro {
  nivel: NivelId | null;
  regioes: readonly Regiao[];
}

/**
 * Esmaece o território quando seu nível está desmarcado. Uma região de alerta mais grave mantém o
 * país à vista enquanto o nível dessa região estiver marcado (Líbano com só "não viaje", FR-027).
 * Áreas neutras não têm nível e nunca esmaecem.
 */
export function territorioEsmaecido(
  territorio: TerritorioParaFiltro,
  niveisMarcados: readonly NivelId[],
): boolean {
  if (territorio.nivel === null) return false;
  if (niveisMarcados.includes(territorio.nivel)) return false;
  return !territorio.regioes.some((regiao) => niveisMarcados.includes(regiao.nivel));
}

export function nenhumNivelMarcado(niveisMarcados: readonly NivelId[]): boolean {
  return niveisMarcados.length === 0;
}

/** Marca o nível se estava desmarcado e desmarca se estava marcado. */
export function alternarNivel(niveisMarcados: readonly NivelId[], nivel: NivelId): NivelId[] {
  return niveisMarcados.includes(nivel)
    ? niveisMarcados.filter((n) => n !== nivel)
    : [...niveisMarcados, nivel];
}
