/**
 * Geometria dos territórios (public/geo/territorios.geojson, contrato em
 * specs/.../contracts/geometria-territorios.md) e a mistura dela com os níveis vindos de /mapa.
 */
import { COR_SEM_PREENCHIMENTO, SEM_PREENCHIMENTO, paletaDe, preenchimentoDeAlerta } from "./cor";
import { nomeDaImagem } from "./padroes";
import type {
  ModoDoGlobo,
  PadraoDoPreenchimento,
  Preenchimento,
  TerritorioDesenhado,
} from "./tipos";

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
  /** O mapa desenha o padrão por cima da cor de base. */
  padrao: PadraoDoPreenchimento | null;
  /** Nome da imagem do padrão; ausente quando o território não tem padrão. */
  imagem_do_padrao?: string;
  /** O território não é pintado (vistos carregando ou com erro); nunca o cinza de "sem informação". */
  sem_preenchimento: boolean;
  /** Cor da borda regional; ausente quando o território não tem região em destaque. */
  borda_regional?: string;
  /** Só existe com o modo daltonismo e borda de "evite": tira a feição da camada contínua. */
  borda_tracejada?: true;
  /** Filtro de níveis (FR-025): o mapa reduz a opacidade, mantendo a cor do nível. */
  esmaecido: boolean;
}

/**
 * Território que a lista não traz: no modo Alertas fica "não verificado" (como na 001); no modo
 * Vistos fica sem preenchimento, porque ainda não se sabe nada dele. Área neutra tem cor própria.
 */
function preenchimentoPadrao(tipo: string, modo: ModoDoGlobo, daltonismo: boolean): Preenchimento {
  if (tipo === "neutro" || modo === "alertas") {
    return preenchimentoDeAlerta(tipo, undefined, daltonismo);
  }
  return SEM_PREENCHIMENTO;
}

export function montarFeicoes(
  geometria: Geometria,
  territorios: readonly TerritorioDesenhado[],
  modo: ModoDoGlobo = "alertas",
  daltonismo = false,
): Colecao<PropriedadesDesenhadas> {
  const { bordas } = paletaDe(daltonismo);
  const porCodigo = new Map(territorios.map((t) => [t.codigo, t]));
  return {
    type: "FeatureCollection",
    features: geometria.features.map((feicao) => {
      const desenhado = porCodigo.get(feicao.properties.codigo);
      const { tipo } = feicao.properties;
      // Área neutra tem cor própria, qualquer que seja o preenchimento recebido
      const preenchimento =
        tipo === "neutro" || desenhado === undefined
          ? preenchimentoPadrao(tipo, modo, daltonismo)
          : desenhado.preenchimento;
      const propriedades: PropriedadesDesenhadas = {
        ...feicao.properties,
        cor: preenchimento.cor ?? COR_SEM_PREENCHIMENTO,
        padrao: preenchimento.padrao,
        sem_preenchimento: preenchimento.cor === null,
        esmaecido: desenhado?.esmaecido ?? false,
      };
      if (preenchimento.padrao !== null) {
        propriedades.imagem_do_padrao = nomeDaImagem(preenchimento.padrao, daltonismo);
      }
      if (desenhado?.bordaRegional) {
        propriedades.borda_regional = bordas[desenhado.bordaRegional];
        if (daltonismo && desenhado.bordaRegional === "evitar") propriedades.borda_tracejada = true;
      }
      return { type: "Feature", properties: propriedades, geometry: feicao.geometry };
    }),
  };
}
