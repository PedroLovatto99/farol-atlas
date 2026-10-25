/**
 * Endereços que vêm da API (links de alertas, fontes de contato) são dados externos: só viram link
 * se forem http ou https. Qualquer outro esquema (javascript:, data:) fica como texto (princípio VIII).
 */
export function ehUrlWeb(valor: string): boolean {
  try {
    const { protocol } = new URL(valor);
    return protocol === "https:" || protocol === "http:";
  } catch {
    return false;
  }
}
