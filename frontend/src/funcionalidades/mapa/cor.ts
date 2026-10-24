/** Cores do mapa: funções puras, sem MapLibre. Os valores repetem os tokens de tema.css. */
import { NIVEIS, NIVEL_PADRAO, type NivelId } from "../../compartilhado/niveis";
import type { Regiao } from "../../servicos/api/cliente";
import type { BordaRegional } from "./tipos";

/** Antártida, Saara Ocidental e outras áreas sem soberania reconhecida (FR-032). */
export const COR_DA_AREA_NEUTRA = "#F1EFE8";

/** Borda de destaque do país com uma região mais grave (FR-004). */
export const COR_DA_BORDA_REGIONAL: Readonly<Record<BordaRegional, string>> = {
  nao_viajar: "#A32D2D",
  evitar: "#854F0B",
};

/**
 * Cor de preenchimento. Sem informação do nível o padrão é "não verificado", nunca "sem alerta"
 * (princípio V); área neutra tem cor própria e não tem nível.
 */
export function corDoTerritorio(tipo: string, nivel: NivelId | undefined): string {
  if (tipo === "neutro") return COR_DA_AREA_NEUTRA;
  return NIVEIS[nivel ?? NIVEL_PADRAO].cor;
}

/** A região mais grave decide a borda: "não viaje" vale mais que "evite". */
export function bordaRegionalDe(regioes: readonly Regiao[]): BordaRegional | null {
  if (regioes.some((r) => r.nivel === "nao_viajar")) return "nao_viajar";
  if (regioes.some((r) => r.nivel === "evitar")) return "evitar";
  return null;
}
