import { useConsultaDeMidia } from "./useConsultaDeMidia";

/** Verdadeiro quando o sistema pede movimento reduzido: animações do mapa e do painel desligam. */
export function useMovimentoReduzido(): boolean {
  return useConsultaDeMidia("(prefers-reduced-motion: reduce)");
}
