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
