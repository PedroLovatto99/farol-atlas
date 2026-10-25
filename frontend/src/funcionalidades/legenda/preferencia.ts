/**
 * Lembra se a pessoa recolheu ou abriu a legenda. O `localStorage` pode não existir ou lançar erro
 * (janela privada, dados do site bloqueados): nesse caso a legenda segue a regra da largura da
 * tela e funciona do mesmo jeito, só não lembra.
 */

export const CHAVE_DA_LEGENDA = "farol-atlas:legenda";

/** `true` aberta, `false` recolhida, `null` sem escolha guardada (vale a largura da tela). */
export function lerPreferenciaDaLegenda(): boolean | null {
  try {
    const valor = window.localStorage.getItem(CHAVE_DA_LEGENDA);
    if (valor === "aberta") return true;
    if (valor === "fechada") return false;
  } catch {
    // sem acesso ao armazenamento: segue a largura da tela
  }
  return null;
}

export function gravarPreferenciaDaLegenda(aberta: boolean): void {
  try {
    window.localStorage.setItem(CHAVE_DA_LEGENDA, aberta ? "aberta" : "fechada");
  } catch {
    // não lembrar não pode quebrar a legenda
  }
}
