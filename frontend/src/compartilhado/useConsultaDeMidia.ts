import { useSyncExternalStore } from "react";

/** Acompanha uma consulta de mídia CSS (ex.: preferência por movimento reduzido). */
export function useConsultaDeMidia(consulta: string): boolean {
  return useSyncExternalStore(
    (avisar) => {
      const lista = window.matchMedia(consulta);
      lista.addEventListener("change", avisar);
      return () => lista.removeEventListener("change", avisar);
    },
    () => window.matchMedia(consulta).matches,
    () => false,
  );
}
