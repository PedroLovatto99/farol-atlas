/**
 * Busca de territórios pelo nome (FR-019 a FR-023): funções puras, sem diferença de acento nem de
 * maiúsculas. O índice vem dos territórios de `/mapa`, então esmaecidos pelo filtro também entram.
 */
import type { TerritorioNoMapa } from "../../servicos/api/cliente";

export interface ResultadoDaBusca {
  codigo: string;
  /** Texto da sugestão, ex.: "Kosovo (Sérvia)". */
  rotulo: string;
}

/** Sugestões demais atrapalham no celular. */
export const MAXIMO_DE_SUGESTOES = 8;

/** Minúsculas, sem acento e sem espaços nas pontas (NFKD separa a letra do acento). */
export function normalizar(texto: string): string {
  return texto
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

/** 0 = algum nome começa com o termo; 1 = só contém; null = não casa. */
function pontuacao(textos: readonly string[], termo: string): 0 | 1 | null {
  let melhor: 0 | 1 | null = null;
  for (const texto of textos) {
    const normalizado = normalizar(texto);
    if (normalizado.startsWith(termo)) return 0;
    if (normalizado.includes(termo)) melhor = 1;
  }
  return melhor;
}

/**
 * Territórios que casam com o termo no `nome`, no `rotulo_busca` ou nos `termos_busca` (é assim
 * que "Kosovo" e "Malvinas" são achados). Quem começa com o termo vem antes de quem só o contém;
 * dentro de cada grupo vale a ordem de `/mapa`. Busca vazia não sugere nada.
 */
export function buscarTerritorios(
  territorios: readonly TerritorioNoMapa[],
  termo: string,
): ResultadoDaBusca[] {
  const procurado = normalizar(termo);
  if (procurado === "") return [];

  const casados: { resultado: ResultadoDaBusca; pontos: 0 | 1 }[] = [];
  for (const t of territorios) {
    const pontos = pontuacao([t.nome, t.rotulo_busca, ...t.termos_busca], procurado);
    if (pontos !== null) {
      casados.push({ resultado: { codigo: t.codigo, rotulo: t.rotulo_busca }, pontos });
    }
  }
  // sort é estável: dentro do mesmo grupo a ordem de entrada se mantém
  casados.sort((a, b) => a.pontos - b.pontos);
  return casados.slice(0, MAXIMO_DE_SUGESTOES).map((c) => c.resultado);
}
