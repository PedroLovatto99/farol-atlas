/**
 * Vistos para brasileiros (feature 002): as categorias, seus rótulos em português e os textos fixos
 * da interface. As cores e as chaves da legenda do modo "Vistos" entram junto do globo (P2).
 */
import type { SituacaoDeVisto } from "../servicos/api/cliente";

/** Toda categoria aparece também como texto: a cor nunca é a única informação (princípio VI). */
export const ROTULOS_DE_VISTO: Readonly<Record<SituacaoDeVisto, string>> = {
  isento: "Isento de visto",
  visto_na_chegada: "Visto na chegada",
  autorizacao_eletronica: "Autorização ou visto eletrônico",
  visto_exigido: "Visto exigido",
  outra_situacao: "Outra situação",
  sem_informacao: "Sem informação de visto",
};

/**
 * Da menos para a mais exigente (FR-007). "Outra situação" e "sem informação" ficam fora da ordem:
 * nunca são tratadas como a categoria mais favorável (princípio V).
 */
export const ORDEM_DE_EXIGENCIA = [
  "isento",
  "visto_na_chegada",
  "autorizacao_eletronica",
  "visto_exigido",
] as const satisfies readonly SituacaoDeVisto[];

/** FR-009: a informação vem de um site colaborativo e precisa ser conferida antes da viagem. */
export const AVISO_DE_FONTE_NAO_OFICIAL =
  "Informação não oficial. Confirme com o consulado ou embaixada do país antes da viagem.";

/** FR-006: além da categoria, a seção diz que basta o documento de identidade. */
export const ENTRADA_COM_RG = "Entrada com o RG";

/** FR-007a */
export const VARIA_CONFORME_O_MOTIVO = "Varia conforme o motivo da viagem";
export const PERMANENCIA_VARIA_CONFORME_O_MOTIVO = "Varia conforme o motivo (ver observações)";

/** FR-007: o sistema não escolhe um dos prazos. */
export const PERMANENCIA_DIVERGENTE = "Prazos divergentes na fonte (ver observações)";

/** FR-004a e FR-005 */
export const TEXTO_TRADUCAO_AUTOMATICA = "tradução automática";
export const TEXTO_NAO_TRADUZIDO = "não traduzido";

/** FR-011: sem dado, nunca uma categoria, e a falta de dado não é permissão de entrada. */
export const TEXTO_SEM_INFORMACAO_DE_VISTO =
  "Não há informação de visto para este país. Isso não significa que a entrada seja livre.";

/** FR-015 */
export const AVISO_DE_VISTO_DESATUALIZADO =
  "Estes dados podem estar desatualizados: foram lidos da fonte há mais de 14 dias.";

/** As cinco categorias com cor própria no globo, mais "sem informação" (cinza). Do amarelo ao roxo escuro: mais escuro, mais exigente. */
export const CORES_DE_VISTO: Readonly<Record<SituacaoDeVisto, string>> = {
  isento: "#FEDD50",
  visto_na_chegada: "#D17DA4",
  autorizacao_eletronica: "#8F5FCC",
  visto_exigido: "#3B1C6B",
  outra_situacao: "#948878",
  sem_informacao: "#BEBAB1",
};

/** O Brasil e as áreas neutras: o neutro que já existe, distinto do cinza de "sem informação". */
export const COR_DO_BRASIL_NO_MODO_VISTOS = "#F1EFE8";
/** Listras do "Isento, entrada com RG" (a base é a cor do "Isento"). */
export const COR_DAS_LISTRAS = "#1F2A44";
/** Borda das amostras da legenda: "Isento" e "sem informação" ficam abaixo de 3:1 contra o branco. */
export const COR_DA_BORDA_DA_AMOSTRA = "#5F5E5A";
/** Contorno dos países no modo "Vistos": escuro e opaco, para o contraste de objeto gráfico (1.4.11). */
export const COR_DO_CONTORNO_NO_MODO_VISTOS = "#1F2A44";
/** O oceano do mapa, contra o qual as cores de visto também precisam se distinguir. */
export const COR_DO_OCEANO = "#DCE8F2";

/**
 * Chaves da legenda do modo "Vistos", na ordem de exibição. `isento_rg` é um subitem de `isento`:
 * não é uma categoria nova, só o filtro dos isentos que aceitam o RG (FR-022a).
 */
export type ChaveDeVisto =
  | "isento"
  | "isento_rg"
  | "visto_na_chegada"
  | "autorizacao_eletronica"
  | "visto_exigido"
  | "outra_situacao"
  | "sem_informacao";

export const CHAVES_DA_LEGENDA_DE_VISTOS: readonly ChaveDeVisto[] = [
  "isento",
  "isento_rg",
  "visto_na_chegada",
  "autorizacao_eletronica",
  "visto_exigido",
  "outra_situacao",
  "sem_informacao",
];

/** Todas as chaves marcadas: o estado da legenda ao abrir o site. */
export const TODAS_AS_CHAVES_DE_VISTO: readonly ChaveDeVisto[] = CHAVES_DA_LEGENDA_DE_VISTOS;

export const ROTULOS_DA_LEGENDA_DE_VISTOS: Readonly<Record<ChaveDeVisto, string>> = {
  isento: ROTULOS_DE_VISTO.isento,
  isento_rg: "Isento, entrada com RG",
  visto_na_chegada: ROTULOS_DE_VISTO.visto_na_chegada,
  autorizacao_eletronica: ROTULOS_DE_VISTO.autorizacao_eletronica,
  visto_exigido: ROTULOS_DE_VISTO.visto_exigido,
  outra_situacao: ROTULOS_DE_VISTO.outra_situacao,
  sem_informacao: ROTULOS_DE_VISTO.sem_informacao,
};

/** Texto do item informativo (sem caixa) do Brasil na legenda (FR-023). */
export const TEXTO_DO_BRASIL_NA_LEGENDA = "Brasil: seu país, sem seção de visto";
