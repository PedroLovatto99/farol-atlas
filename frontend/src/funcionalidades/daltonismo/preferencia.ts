/**
 * Lembra o modo daltonismo entre visitas. O `localStorage` pode não existir ou lançar erro (janela
 * privada, dados do site bloqueados): nesse caso o modo funciona na visita, só não lembra (FR-012).
 */

export const CHAVE_DO_DALTONISMO = "farol-atlas:daltonismo";

/** Só "ligado" liga: qualquer outro valor guardado vale desligado. */
export function lerPreferenciaDoDaltonismo(): boolean {
  try {
    return window.localStorage.getItem(CHAVE_DO_DALTONISMO) === "ligado";
  } catch {
    return false;
  }
}

export function gravarPreferenciaDoDaltonismo(ligado: boolean): void {
  try {
    window.localStorage.setItem(CHAVE_DO_DALTONISMO, ligado ? "ligado" : "desligado");
  } catch {
    // não lembrar não pode quebrar o botão
  }
}
