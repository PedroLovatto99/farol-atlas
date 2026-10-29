/** Cores do mapa: funções puras, sem MapLibre. Os valores repetem os tokens de tema.css. */
import { NIVEIS, NIVEL_PADRAO, type NivelId } from "../../compartilhado/niveis";
import {
  COR_DO_BRASIL_NO_MODO_VISTOS,
  COR_DO_OCEANO,
  CORES_DE_VISTO,
} from "../../compartilhado/vistos";
import type { Regiao, SituacaoNoGlobo } from "../../servicos/api/cliente";
import type { BordaRegional, Preenchimento } from "./tipos";

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

/** Sem preenchimento: o oceano aparece por baixo (carregando ou erro dos vistos); nunca o cinza. */
export const SEM_PREENCHIMENTO: Preenchimento = { cor: null, padrao: null };

/** Valor da propriedade `cor` de uma feição sem preenchimento; o mapa a desenha com opacidade 0. */
export const COR_SEM_PREENCHIMENTO = COR_DO_OCEANO;

/** O modo "Alertas": exatamente as cores da 001, sem padrão. */
export function preenchimentoDeAlerta(tipo: string, nivel: NivelId | undefined): Preenchimento {
  return { cor: corDoTerritorio(tipo, nivel), padrao: null };
}

/**
 * O modo "Vistos". `situacao` nula quer dizer que não há vistos para pintar (carregando ou erro):
 * o território fica sem preenchimento, nunca em cinza, que só significa "sem informação de visto".
 * Área neutra e Brasil ficam no neutro. Só o "Isento" que aceita o RG ganha as listras.
 */
export function preenchimentoDeVisto(
  tipo: string,
  situacao: SituacaoNoGlobo | null,
  aceitaRg: boolean,
): Preenchimento {
  const neutro: Preenchimento = { cor: COR_DO_BRASIL_NO_MODO_VISTOS, padrao: null };
  if (tipo === "neutro" || situacao === "nao_se_aplica") return neutro;
  if (situacao === null) return SEM_PREENCHIMENTO;
  return { cor: CORES_DE_VISTO[situacao], padrao: situacao === "isento" && aceitaRg ? "rg" : null };
}
