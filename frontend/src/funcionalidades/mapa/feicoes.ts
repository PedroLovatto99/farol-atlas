/**
 * Geometria dos territórios (public/geo/territorios.geojson, contrato em
 * specs/.../contracts/geometria-territorios.md) e a mistura dela com os níveis vindos de /mapa.
 */
import {
  COR_DA_BORDA_REGIONAL,
  COR_SEM_PREENCHIMENTO,
  SEM_PREENCHIMENTO,
  preenchimentoDeAlerta,
} from "./cor";
import type { ModoDoGlobo, Preenchimento, TerritorioDesenhado } from "./tipos";

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

/** O que o MapLibre desenha: as propriedades da geometria mais cor, padrão e borda regional. */
export interface PropriedadesDesenhadas extends PropriedadesDaGeometria {
  cor: string;
  /** "rg": o mapa desenha as listras por cima da cor de base ("Isento, entrada com RG"). */
  padrao: "rg" | null;
  /** O território não é pintado (vistos carregando ou com erro); nunca o cinza de "sem informação". */
  sem_preenchimento: boolean;
  /** Cor da borda regional; ausente quando o território não tem região em destaque. */
  borda_regional?: string;
  /** Filtro de níveis (FR-025): o mapa reduz a opacidade, mantendo a cor do nível. */
  esmaecido: boolean;
}

/**
 * Território que a lista não traz: no modo Alertas fica "não verificado" (como na 001); no modo
 * Vistos fica sem preenchimento, porque ainda não se sabe nada dele. Área neutra tem cor própria.
 */
function preenchimentoPadrao(tipo: string, modo: ModoDoGlobo): Preenchimento {
  if (tipo === "neutro" || modo === "alertas") return preenchimentoDeAlerta(tipo, undefined);
  return SEM_PREENCHIMENTO;
}

export function montarFeicoes(
  geometria: Geometria,
  territorios: readonly TerritorioDesenhado[],
  modo: ModoDoGlobo = "alertas",
): Colecao<PropriedadesDesenhadas> {
  const porCodigo = new Map(territorios.map((t) => [t.codigo, t]));
  return {
    type: "FeatureCollection",
    features: geometria.features.map((feicao) => {
      const desenhado = porCodigo.get(feicao.properties.codigo);
      const { tipo } = feicao.properties;
      // Área neutra tem cor própria, qualquer que seja o preenchimento recebido
      const preenchimento =
        tipo === "neutro" || desenhado === undefined
          ? preenchimentoPadrao(tipo, modo)
          : desenhado.preenchimento;
      const propriedades: PropriedadesDesenhadas = {
        ...feicao.properties,
        cor: preenchimento.cor ?? COR_SEM_PREENCHIMENTO,
        padrao: preenchimento.padrao,
        sem_preenchimento: preenchimento.cor === null,
        esmaecido: desenhado?.esmaecido ?? false,
      };
      if (desenhado?.bordaRegional) {
        propriedades.borda_regional = COR_DA_BORDA_REGIONAL[desenhado.bordaRegional];
      }
      return { type: "Feature", properties: propriedades, geometry: feicao.geometry };
    }),
  };
}
