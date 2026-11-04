/** Cores do mapa: funções puras, sem MapLibre. Os valores repetem os tokens de tema.css. */
import { NIVEIS, NIVEL_PADRAO, type NivelId } from "../../compartilhado/niveis";
import {
  COR_DAS_LISTRAS,
  COR_DO_BRASIL_NO_MODO_VISTOS,
  COR_DO_OCEANO,
  CORES_DE_VISTO,
} from "../../compartilhado/vistos";
import type { Regiao, SituacaoDeVisto, SituacaoNoGlobo } from "../../servicos/api/cliente";
import type { BordaRegional, Preenchimento } from "./tipos";

/** Antártida, Saara Ocidental e outras áreas sem soberania reconhecida (FR-032). */
export const COR_DA_AREA_NEUTRA = "#F1EFE8";

/** Borda de destaque do país com uma região mais grave (FR-004). */
export const COR_DA_BORDA_REGIONAL: Readonly<Record<BordaRegional, string>> = {
  nao_viajar: "#A32D2D",
  evitar: "#854F0B",
};

/** Marcas da hachura e dos pontos do modo daltonismo; o modo desligado não tem padrões de alerta. */
export const COR_DAS_MARCAS = "#18142C";

/** As cores que mudam com o modo daltonismo. Neutro e oceano ficam de fora: nunca mudam (FR-007). */
export interface Paleta {
  niveis: Readonly<Record<NivelId, string>>;
  bordas: Readonly<Record<BordaRegional, string>>;
  vistos: Readonly<Record<SituacaoDeVisto, string>>;
  listras: string;
}

const PALETA_PADRAO: Paleta = {
  niveis: {
    sem_alerta: NIVEIS.sem_alerta.cor,
    evitar: NIVEIS.evitar.cor,
    nao_viajar: NIVEIS.nao_viajar.cor,
    nao_verificado: NIVEIS.nao_verificado.cor,
  },
  bordas: COR_DA_BORDA_REGIONAL,
  vistos: CORES_DE_VISTO,
  listras: COR_DAS_LISTRAS,
};

/** Contrato em specs/004-modo-daltonismo/contracts/paletas-e-padroes.md; repete os tokens do tema. */
const PALETA_DO_DALTONISMO: Paleta = {
  niveis: {
    sem_alerta: "#8CCDFB",
    evitar: "#F1D25F",
    nao_viajar: "#E4605B",
    nao_verificado: "#878C92",
  },
  bordas: { nao_viajar: "#861212", evitar: "#8C641A" },
  vistos: CORES_DE_VISTO,
  listras: "#0E2A20",
};

export function paletaDe(daltonismo: boolean): Paleta {
  return daltonismo ? PALETA_DO_DALTONISMO : PALETA_PADRAO;
}

/**
 * Cor de preenchimento. Sem informação do nível o padrão é "não verificado", nunca "sem alerta"
 * (princípio V); área neutra tem cor própria e não tem nível.
 */
export function corDoTerritorio(
  tipo: string,
  nivel: NivelId | undefined,
  daltonismo = false,
): string {
  if (tipo === "neutro") return COR_DA_AREA_NEUTRA;
  return paletaDe(daltonismo).niveis[nivel ?? NIVEL_PADRAO];
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

/**
 * O modo "Alertas": exatamente as cores da 001, sem padrão. Com o modo daltonismo, "não viaje" e
 * "evite" ganham padrão, para a leitura não depender só da cor (FR-009).
 */
export function preenchimentoDeAlerta(
  tipo: string,
  nivel: NivelId | undefined,
  daltonismo = false,
): Preenchimento {
  const comPadrao =
    daltonismo && tipo !== "neutro" && (nivel === "nao_viajar" || nivel === "evitar");
  return { cor: corDoTerritorio(tipo, nivel, daltonismo), padrao: comPadrao ? nivel : null };
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
  daltonismo = false,
): Preenchimento {
  const neutro: Preenchimento = { cor: COR_DO_BRASIL_NO_MODO_VISTOS, padrao: null };
  if (tipo === "neutro" || situacao === "nao_se_aplica") return neutro;
  if (situacao === null) return SEM_PREENCHIMENTO;
  return {
    cor: paletaDe(daltonismo).vistos[situacao],
    padrao: situacao === "isento" && aceitaRg ? "rg" : null,
  };
}
