/**
 * Enquadramento da câmera ao selecionar um território (FR-009): função pura, sem MapLibre.
 *
 * Usa só a maior parte de cada território, para que países com ultramar ou que cruzam a
 * antimeridiana (França, Rússia) não mostrem o mundo inteiro. Kosovo e Malvinas usam o grupo
 * `zoom` do soberano, que vem das propriedades da geometria.
 */
import type { Geometria } from "./feicoes";
import type { Caixa, Margem, PedidoDeCamera } from "./tipos";

export const ZOOM_MAXIMO = 5.5;
/** Juntar o posto responsável só vale se a caixa ficar mais estreita que isto (em graus). */
export const LIMITE_DE_LARGURA = 180;

const DURACAO_DO_MOVIMENTO = 1600;
const FRACAO_DA_GAVETA = 0.55;
/** O aviso de site não oficial fica sobre o mapa, no topo; o enquadramento deixa essa faixa livre. */
const TOPO_DO_COMPUTADOR = 100;
const TOPO_DO_CELULAR = 150; // o aviso quebra em mais linhas na tela estreita

export type PedidoDeEnquadramento = Extract<PedidoDeCamera, { tipo: "enquadrar" }>;

type Posicao = readonly [number, number];
type Limites = readonly [oeste: number, sul: number, leste: number, norte: number];

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function lerAnel(valor: unknown): Posicao[] | null {
  if (!Array.isArray(valor)) return null;
  const anel: Posicao[] = [];
  for (const ponto of valor as unknown[]) {
    if (!Array.isArray(ponto)) return null;
    const [x, y] = ponto as unknown[];
    if (typeof x !== "number" || typeof y !== "number") return null;
    anel.push([x, y]);
  }
  return anel;
}

/** Anéis externos de cada polígono da geometria (Polygon ou MultiPolygon). */
function aneisExternos(geometria: unknown): Posicao[][] {
  if (!ehObjeto(geometria) || !Array.isArray(geometria["coordinates"])) return [];
  const coordenadas = geometria["coordinates"] as unknown[];
  const poligonos =
    geometria["type"] === "Polygon"
      ? [coordenadas]
      : geometria["type"] === "MultiPolygon"
        ? coordenadas
        : [];
  const aneis: Posicao[][] = [];
  for (const poligono of poligonos) {
    if (!Array.isArray(poligono)) continue;
    const anel = lerAnel((poligono as unknown[])[0]);
    if (anel !== null && anel.length > 0) aneis.push(anel);
  }
  return aneis;
}

function area(anel: readonly Posicao[]): number {
  let soma = 0;
  anel.forEach(([x1, y1], i) => {
    const [x2, y2] = anel[(i + 1) % anel.length] ?? [x1, y1];
    soma += x1 * y2 - x2 * y1;
  });
  return Math.abs(soma / 2);
}

function limitesDaMaiorParte(geometria: unknown): Limites | null {
  const aneis = aneisExternos(geometria);
  const maior = aneis.reduce<Posicao[] | null>(
    (atual, anel) => (atual === null || area(anel) > area(atual) ? anel : atual),
    null,
  );
  if (maior === null) return null;
  const xs = maior.map(([x]) => x);
  const ys = maior.map(([, y]) => y);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

function unir(a: Limites | null, b: Limites): Limites {
  if (a === null) return b;
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])];
}

interface Entrada {
  geometria: Geometria;
  /** Território tocado. */
  codigo: string;
  /** Posto responsável, em outro país, quando o território não tem posto (FR-018). */
  responsavel: { latitude: number; longitude: number } | null;
  margem: Margem;
}

/** `null` quando não há o que enquadrar (código desconhecido ou área neutra). */
export function calcularEnquadramento({
  geometria,
  codigo,
  responsavel,
  margem,
}: Entrada): PedidoDeEnquadramento | null {
  const feicao = geometria.features.find((f) => f.properties.codigo === codigo);
  if (feicao === undefined) return null;
  const grupo = feicao.properties.zoom ?? (feicao.properties.tipo === "neutro" ? null : codigo);
  if (grupo === null) return null;

  let limites: Limites | null = null;
  for (const f of geometria.features) {
    if (f.properties.zoom !== grupo) continue;
    const parte = limitesDaMaiorParte(f.geometry);
    if (parte !== null) limites = unir(limites, parte);
  }
  if (limites === null) return null;

  if (responsavel !== null) {
    const junto = unir(limites, [
      responsavel.longitude,
      responsavel.latitude,
      responsavel.longitude,
      responsavel.latitude,
    ]);
    // no Pacífico, juntar daria a volta ao mundo
    if (junto[2] - junto[0] < LIMITE_DE_LARGURA) limites = junto;
  }

  const [oeste, sul, leste, norte] = limites;
  const caixa: Caixa = [
    [oeste, sul],
    [leste, norte],
  ];
  return { tipo: "enquadrar", caixa, margem, zoomMaximo: ZOOM_MAXIMO };
}

/**
 * Margem da câmera conforme o layout: no computador o painel fica à direita; no celular a gaveta
 * ocupa a parte de baixo.
 */
export function margemDoLayout(celular: boolean, alturaDaJanela: number): Margem {
  return celular
    ? {
        topo: TOPO_DO_CELULAR,
        esquerda: 20,
        direita: 20,
        baixo: Math.round(alturaDaJanela * FRACAO_DA_GAVETA),
      }
    : { topo: TOPO_DO_COMPUTADOR, esquerda: 20, direita: 380, baixo: 20 };
}

/** Espaço que a barra do painel recolhido ocupa no rodapé do celular: 59 px de barra, 8 de margem e folga. */
const ALTURA_DA_BARRA_NO_CELULAR = 80;
const FOLGA_DO_TOPO = 8;

/** Centro da caixa de um enquadramento: o ponto onde fica o país, para centralizá-lo sem mudar o zoom. */
export function centroDoEnquadramento(pedido: PedidoDeEnquadramento): {
  latitude: number;
  longitude: number;
} {
  const [[oeste, sul], [leste, norte]] = pedido.caixa;
  return { latitude: (sul + norte) / 2, longitude: (oeste + leste) / 2 };
}

interface EntradaDaAreaLivre {
  alturaDaJanela: number;
  /** Onde terminam os controles do topo (aviso, busca, seletor), em pixels; 0 se não foi medido. */
  fimDoCabecalho: number;
  /** O painel que vai ocupar o rodapé: a barra (recolhido) ou a gaveta de 55% (expandido). */
  painelRecolhido: boolean;
}

/**
 * Margem da área visível do celular depois de recolher ou expandir o painel (FR-030): de baixo dos
 * controles do topo até o painel, que é a barra ou a gaveta.
 */
export function margemDaAreaLivre({
  alturaDaJanela,
  fimDoCabecalho,
  painelRecolhido,
}: EntradaDaAreaLivre): Margem {
  return {
    topo: fimDoCabecalho > 0 ? Math.ceil(fimDoCabecalho) + FOLGA_DO_TOPO : TOPO_DO_CELULAR,
    esquerda: 20,
    direita: 20,
    baixo: painelRecolhido
      ? ALTURA_DA_BARRA_NO_CELULAR
      : Math.round(alturaDaJanela * FRACAO_DA_GAVETA),
  };
}

/** Duração dos movimentos de câmera: nenhuma com a preferência por movimento reduzido (FR-039). */
export function duracaoDoMovimento(reduzirMovimento: boolean): number {
  return reduzirMovimento ? 0 : DURACAO_DO_MOVIMENTO;
}
