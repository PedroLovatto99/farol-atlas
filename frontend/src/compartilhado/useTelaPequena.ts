import { useConsultaDeMidia } from "./useConsultaDeMidia";

/** Largura máxima, em px, tratada como celular (o painel vira gaveta). */
export const LARGURA_MAXIMA_DO_CELULAR = 700;

export function useTelaPequena(): boolean {
  return useConsultaDeMidia(`(max-width: ${LARGURA_MAXIMA_DO_CELULAR}px)`);
}
