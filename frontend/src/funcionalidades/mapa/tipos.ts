/**
 * Interface do componente de mapa (specs/001-mapa-alertas-viagem/contracts/mapa-props.md).
 *
 * A biblioteca do mapa fica isolada atrás desta interface (princípio III): só o adaptador importa
 * `maplibre-gl`. Trocá-la não pode exigir mudança em painel, busca, legenda nem no estado.
 */
import type { TipoPosto } from "../../servicos/api/cliente";

export type CodigoTerritorio = string;

/** Nível de uma região com alerta mais grave (FR-004). */
export type BordaRegional = "nao_viajar" | "evitar";

/** O que o globo mostra: os alertas da 001 ou os vistos da 002 (nunca guardado entre visitas). */
export type ModoDoGlobo = "alertas" | "vistos";

/**
 * Como um território é pintado. O adaptador só executa; a cor e o padrão são calculados fora dele
 * (`preenchimentoDeAlerta`, `preenchimentoDeVisto`).
 */
export interface Preenchimento {
  /** Cor de base, em hex. `null`: sem preenchimento (carregando ou erro dos vistos), nunca cinza. */
  cor: string | null;
  /** "rg": listras sobre a cor de base ("Isento, entrada com RG"); `null`: cor lisa. */
  padrao: "rg" | null;
}

export interface TerritorioDesenhado {
  /** Código da feição na geometria. */
  codigo: CodigoTerritorio;
  preenchimento: Preenchimento;
  /** Sempre nula no modo Vistos (FR-025). */
  bordaRegional: BordaRegional | null;
  /** Filtro da legenda do modo ativo (FR-025 da 001, FR-024), calculado fora do mapa. */
  esmaecido: boolean;
}

export interface PostoDesenhado {
  /** Ícone compartilhado por postos na mesma coordenada (FR-018d). */
  grupo: string;
  /** Cidade do ícone, para o nome acessível. */
  cidade: string;
  latitude: number;
  longitude: number;
  /** Mais de um quando dois postos dividem o ícone. */
  tipos: readonly TipoPosto[];
  territorios: readonly CodigoTerritorio[];
}

export interface PaisSemPostoDesenhado {
  territorio: CodigoTerritorio;
  /** Nome do país, para o nome acessível do ícone. */
  nome: string;
  latitude: number;
  longitude: number;
  /** Ponto e ícone do posto responsável, para a linha tracejada (FR-018). */
  responsavel: { latitude: number; longitude: number; grupo: string } | null;
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
  /** FR-018c: só desloca o centro, sem mudar o zoom. A margem é a área coberta pelo painel. */
  | { tipo: "garantir-visivel"; latitude: number; longitude: number; margem: Margem }
  /**
   * FR-030: no celular, recolher ou expandir o painel leva o país selecionado ao centro da área que
   * sobrou visível (a margem), sempre, sem mudar o zoom.
   */
  | { tipo: "centralizar"; latitude: number; longitude: number; margem: Margem }
  /** FR-018g: tocar num ícone não reenquadra o mapa. */
  | { tipo: "manter" };

export interface MapaProps {
  territorios: readonly TerritorioDesenhado[];
  /**
   * O que o globo mostra. Só decide o que fazer com um território que a lista não traz (alertas:
   * "não verificado", como na 001; vistos: sem preenchimento). Sem ele vale "alertas".
   */
  modo?: ModoDoGlobo;
  postos: readonly PostoDesenhado[];
  paisesSemPosto: readonly PaisSemPostoDesenhado[];

  /** Contorno de seleção. */
  selecionado: CodigoTerritorio | null;
  /** FR-018a: maior, com contorno e à frente; aparece em qualquer zoom (FR-018h). */
  grupoEmDestaque: string | null;
  /** Ícones dos postos que o painel aberto lista: aparecem em qualquer zoom (FR-017). */
  gruposDoPainel: readonly string[];
  /** FR-039 e FR-018f: sem animação. */
  reduzirMovimento: boolean;

  /** Toque num país; áreas neutras e o oceano não chamam (FR-016). */
  onSelecionarTerritorio(codigo: CodigoTerritorio): void;
  /** Toque num ícone (FR-018g): quem chama abre o painel. */
  onSelecionarGrupo(grupo: string): void;
  onLimparSelecao(): void;

  camera: PedidoDeCamera;
}
