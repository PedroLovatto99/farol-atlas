/**
 * Ícones dos postos no mapa (FR-017, FR-018): funções puras, sem MapLibre. Decidem o desenho de
 * cada ícone, quais aparecem e a linha até o posto responsável. O adaptador só as executa.
 */
import type { VarianteDoIcone } from "../../compartilhado/icones-posto";
import type { Mapa, PostoNoMapa, TipoPosto } from "../../servicos/api/cliente";
import { responsavelDe } from "./responsavel";
import type { PaisSemPostoDesenhado, PostoDesenhado } from "./tipos";

/** A partir deste zoom todos os ícones aparecem (FR-017). */
export const ZOOM_DOS_MARCADORES = 3.5;

export type VarianteDoMarcador = VarianteDoIcone;

/** Do mais ao menos importante: define a ordem dos tipos e qual ícone o grupo mostra. */
const ORDEM_DE_TIPO: readonly TipoPosto[] = [
  "Embaixada",
  "Consulado-Geral",
  "Consulado",
  "Vice-Consulado",
  "Escritório de Representação",
  "Escritório Comercial",
];

function ordemDe(tipo: TipoPosto): number {
  return ORDEM_DE_TIPO.indexOf(tipo);
}

/** Os postos na mesma coordenada (`grupo`) dividem um ícone (FR-018d). */
export function agruparPostos(postos: readonly PostoNoMapa[]): PostoDesenhado[] {
  const porGrupo = new Map<string, PostoNoMapa[]>();
  for (const posto of postos) {
    porGrupo.set(posto.grupo, [...(porGrupo.get(posto.grupo) ?? []), posto]);
  }
  return Array.from(porGrupo, ([grupo, doGrupo]) => {
    const primeiro = doGrupo[0] as PostoNoMapa;
    return {
      grupo,
      cidade: primeiro.cidade,
      latitude: primeiro.latitude,
      longitude: primeiro.longitude,
      tipos: doGrupo.map((p) => p.tipo).sort((a, b) => ordemDe(a) - ordemDe(b)),
      territorios: [...new Set(doGrupo.map((p) => p.territorio))],
    };
  });
}

/** Embaixada, consulado (inclui consulado-geral e vice) ou escritório; vale o tipo mais importante. */
export function varianteDoMarcador(
  tipos: readonly TipoPosto[],
): Exclude<VarianteDoMarcador, "sem-posto"> {
  const principal = [...tipos].sort((a, b) => ordemDe(a) - ordemDe(b))[0];
  if (principal === "Embaixada") return "embaixada";
  if (principal === "Escritório de Representação" || principal === "Escritório Comercial") {
    return "escritorio";
  }
  return "consulado";
}

/** Quantos postos além do principal dividem o ícone: o selo "+1" (FR-018d). */
export function seloDoMarcador(tipos: readonly TipoPosto[]): number {
  return Math.max(0, tipos.length - 1);
}

/** Nome acessível do ícone de posto: "Embaixada em Washington e mais 1 posto". */
export function rotuloDoGrupo(posto: Pick<PostoDesenhado, "tipos" | "cidade">): string {
  const principal = [...posto.tipos].sort((a, b) => ordemDe(a) - ordemDe(b))[0] ?? "Posto";
  const outros = seloDoMarcador(posto.tipos);
  const resto = outros === 0 ? "" : ` e mais ${outros} ${outros === 1 ? "posto" : "postos"}`;
  return `${principal} em ${posto.cidade}${resto}`;
}

/** Nome acessível do ícone de país sem posto. */
export function rotuloDoPaisSemPosto(pais: Pick<PaisSemPostoDesenhado, "nome">): string {
  return `${pais.nome}: sem posto brasileiro no país`;
}

/** Países sem posto, com o ponto do ícone e o do posto responsável (FR-018). */
export function paisesSemPostoDesenhados(mapa: Mapa): PaisSemPostoDesenhado[] {
  const nomes = new Map(mapa.territorios.map((t) => [t.codigo, t.nome]));
  return mapa.paises_sem_posto.map((p) => ({
    territorio: p.territorio,
    nome: nomes.get(p.territorio) ?? p.territorio,
    latitude: p.latitude,
    longitude: p.longitude,
    responsavel: responsavelDe(mapa, p.territorio),
  }));
}

/**
 * Linha tracejada do ícone do país sem posto selecionado até o posto responsável, em [lon, lat].
 * Só existe para o país selecionado e quando há posto indicado.
 */
export function linhaAteOResponsavel(
  selecionado: string | null,
  paisesSemPosto: readonly PaisSemPostoDesenhado[],
): [[number, number], [number, number]] | null {
  const pais = paisesSemPosto.find((p) => p.territorio === selecionado);
  if (pais?.responsavel == null) return null;
  return [
    [pais.longitude, pais.latitude],
    [pais.responsavel.longitude, pais.responsavel.latitude],
  ];
}

export interface EntradaDeVisibilidade {
  zoom: number;
  selecionado: string | null;
  /** Ícones dos postos que o painel aberto lista. */
  gruposDoPainel: readonly string[];
  grupoEmDestaque: string | null;
}

/**
 * Ícones de postos que aparecem. A partir do zoom 3,5, todos. Abaixo dele, só os do painel
 * aberto, o do posto responsável do país sem posto selecionado e o que está em destaque, que
 * aparece em qualquer zoom (FR-018e, FR-018h). Os do outro lado do globo o MapLibre esconde.
 */
export function postosVisiveis(
  entrada: EntradaDeVisibilidade,
  postos: readonly PostoDesenhado[],
  paisesSemPosto: readonly PaisSemPostoDesenhado[],
): PostoDesenhado[] {
  if (entrada.zoom >= ZOOM_DOS_MARCADORES) return [...postos];
  const sempre = new Set(entrada.gruposDoPainel);
  if (entrada.grupoEmDestaque !== null) sempre.add(entrada.grupoEmDestaque);
  const responsavel = paisesSemPosto.find((p) => p.territorio === entrada.selecionado)?.responsavel;
  if (responsavel != null) sempre.add(responsavel.grupo);
  return postos.filter((p) => sempre.has(p.grupo));
}

/** Ícones de país sem posto que aparecem: todos a partir do zoom 3,5; antes, só o selecionado. */
export function paisesSemPostoVisiveis(
  entrada: EntradaDeVisibilidade,
  paisesSemPosto: readonly PaisSemPostoDesenhado[],
): PaisSemPostoDesenhado[] {
  if (entrada.zoom >= ZOOM_DOS_MARCADORES) return [...paisesSemPosto];
  return paisesSemPosto.filter((p) => p.territorio === entrada.selecionado);
}
