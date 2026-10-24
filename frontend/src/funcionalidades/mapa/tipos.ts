/**
 * Interface do componente de mapa (specs/001-mapa-alertas-viagem/contracts/mapa-props.md).
 *
 * A biblioteca do mapa fica isolada atrás desta interface (princípio III): só o adaptador importa
 * `maplibre-gl`. Trocá-la não pode exigir mudança em painel, busca, legenda nem no estado.
 */
import type { TipoPosto } from "../../servicos/api/cliente";
import type { NivelId } from "../../compartilhado/niveis";

export type CodigoTerritorio = string;

/** Nível de uma região com alerta mais grave (FR-004). */
export type BordaRegional = "nao_viajar" | "evitar";

export interface TerritorioDesenhado {
  /** Código da feição na geometria. */
  codigo: CodigoTerritorio;
  /** Nível já resolvido pelo backend. */
  nivel: NivelId;
  bordaRegional: BordaRegional | null;
  /** Filtro de níveis (FR-025), calculado fora do mapa. */
  esmaecido: boolean;
}

export interface PostoDesenhado {
  /** Ícone compartilhado por postos na mesma coordenada (FR-018d). */
  grupo: string;
  latitude: number;
  longitude: number;
  /** Mais de um quando dois postos dividem o ícone. */
  tipos: readonly TipoPosto[];
  territorios: readonly CodigoTerritorio[];
}

export interface PaisSemPostoDesenhado {
  territorio: CodigoTerritorio;
  latitude: number;
  longitude: number;
  /** Ponto do posto responsável, para a linha tracejada (FR-018). */
  responsavel: { latitude: number; longitude: number } | null;
}

export interface Margem {
  topo: number;
  esquerda: number;
  direita: number;
  baixo: number;
}

/** [[oeste, sul], [leste, norte]], em graus. */
export type Caixa = readonly [readonly [number, number], readonly [number, number]];

/** Pedido de câmera: o adaptador só o executa; a regra de enquadramento é função pura. */
export type PedidoDeCamera =
  | { tipo: "mundo" }
  | { tipo: "enquadrar"; caixa: Caixa; margem: Margem; zoomMaximo: number }
  /** FR-018c: só desloca o centro, sem mudar o zoom. */
  | { tipo: "garantir-visivel"; latitude: number; longitude: number }
  /** FR-018g: tocar num ícone não reenquadra o mapa. */
  | { tipo: "manter" };

export interface MapaProps {
  territorios: readonly TerritorioDesenhado[];
  postos: readonly PostoDesenhado[];
  paisesSemPosto: readonly PaisSemPostoDesenhado[];

  /** Contorno de seleção. */
  selecionado: CodigoTerritorio | null;
  /** FR-018a: maior, com contorno e à frente; aparece em qualquer zoom (FR-018h). */
  grupoEmDestaque: string | null;
  /** FR-039 e FR-018f: sem animação. */
  reduzirMovimento: boolean;

  /** Toque num país; áreas neutras e o oceano não chamam (FR-016). */
  onSelecionarTerritorio(codigo: CodigoTerritorio): void;
  /** Toque num ícone (FR-018g): quem chama abre o painel. */
  onSelecionarGrupo(grupo: string): void;
  onLimparSelecao(): void;

  camera: PedidoDeCamera;
}
