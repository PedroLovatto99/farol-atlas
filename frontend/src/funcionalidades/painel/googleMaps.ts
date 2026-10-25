import type { TipoPosto } from "../../servicos/api/cliente";

interface DadosDoLocal {
  tipo: TipoPosto;
  cidade: string;
  /** País do posto (no posto responsável, é outro país que não o do painel). */
  pais: string;
  endereco: string | null;
}

/**
 * Link "Abrir no Google Maps" (FR-011, FR-012). Com endereço, usa o endereço; sem ele, usa
 * "tipo do Brasil, cidade, país", que leva à cidade. A consulta é codificada pelo `URL`.
 */
export function urlDoGoogleMaps({ tipo, cidade, pais, endereco }: DadosDoLocal): string {
  const consulta = endereco?.trim() || `${tipo} do Brasil, ${cidade}, ${pais}`;
  const url = new URL("https://www.google.com/maps/search/");
  url.searchParams.set("api", "1");
  url.searchParams.set("query", consulta);
  return url.toString();
}
