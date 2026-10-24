/**
 * Geometria dos territórios (public/geo/territorios.geojson, contrato em
 * specs/.../contracts/geometria-territorios.md) e a mistura dela com os níveis vindos de /mapa.
 */
import { COR_DA_BORDA_REGIONAL, corDoTerritorio } from "./cor";
import type { TerritorioDesenhado } from "./tipos";

export type TipoDaFeicao = "pais" | "dependencia" | "neutro";

export interface PropriedadesDaGeometria {
  codigo: string;
  tipo: TipoDaFeicao;
  /** País soberano de uma dependência. */
  soberano: string | null;
  titulo: string;
  /** Grupo de enquadramento (Kosovo e Malvinas usam o do soberano). */
  zoom: string | null;
}

export interface Feicao<P> {
  type: "Feature";
  properties: P;
  geometry: unknown;
}

export interface Colecao<P> {
  type: "FeatureCollection";
  features: Feicao<P>[];
}

export type Geometria = Colecao<PropriedadesDaGeometria>;

/** O que o MapLibre desenha: as propriedades da geometria mais cor e borda regional. */
export interface PropriedadesDesenhadas extends PropriedadesDaGeometria {
  cor: string;
  /** Cor da borda regional; ausente quando o território não tem região em destaque. */
  borda_regional?: string;
}

export function montarFeicoes(
  geometria: Geometria,
  territorios: readonly TerritorioDesenhado[],
): Colecao<PropriedadesDesenhadas> {
  const porCodigo = new Map(territorios.map((t) => [t.codigo, t]));
  return {
    type: "FeatureCollection",
    features: geometria.features.map((feicao) => {
      const desenhado = porCodigo.get(feicao.properties.codigo);
      const propriedades: PropriedadesDesenhadas = {
        ...feicao.properties,
        cor: corDoTerritorio(feicao.properties.tipo, desenhado?.nivel),
      };
      if (desenhado?.bordaRegional) {
        propriedades.borda_regional = COR_DA_BORDA_REGIONAL[desenhado.bordaRegional];
      }
      return { type: "Feature", properties: propriedades, geometry: feicao.geometry };
    }),
  };
}
