/**
 * As estrelas do fundo do mapa. Função pura: a mesma semente dá sempre o mesmo céu, então o céu
 * não muda entre visitas nem a cada renderização. O desenho fica em `CeuEstrelado.tsx`.
 */

export const SEMENTE_DO_CEU = 20261025;
/** Lado do quadro, em px. O quadro se repete (CSS) para cobrir a tela inteira. */
export const TAMANHO_DO_CEU = 1024;
export const QUANTIDADE_DE_ESTRELAS = 180;
/** Quantas das estrelas são médias e brilhantes; o resto é pequeno e discreto. */
const MEDIAS = 28;
const BRILHANTES = 6;
/** As brilhantes têm halo: ficam longe da borda do quadro para o halo não ser cortado na emenda. */
export const MARGEM_DO_HALO = 10;

export interface Estrela {
  x: number;
  y: number;
  raio: number;
  opacidade: number;
  brilhante: boolean;
  /** Branco com um leve tom azulado ou quente. */
  cor: readonly [number, number, number];
}

const CORES: readonly (readonly [number, number, number])[] = [
  [235, 240, 255],
  [255, 255, 255],
  [200, 218, 255],
  [255, 238, 214],
];

/** mulberry32: gerador pequeno e determinístico (0 <= n < 1). */
function gerador(semente: number): () => number {
  let estado = semente >>> 0;
  return () => {
    estado = (estado + 0x6d2b79f5) >>> 0;
    let t = estado;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function gerarEstrelas(semente: number, quantidade: number, tamanho: number): Estrela[] {
  const sorteio = gerador(semente);
  const entre = (menor: number, maior: number) => menor + sorteio() * (maior - menor);
  const estrelas: Estrela[] = [];
  for (let i = 0; i < quantidade; i++) {
    const brilhante = i < BRILHANTES;
    const media = !brilhante && i < BRILHANTES + MEDIAS;
    const margem = brilhante ? MARGEM_DO_HALO : 0;
    estrelas.push({
      x: entre(margem, tamanho - margem),
      y: entre(margem, tamanho - margem),
      raio: brilhante ? entre(1.3, 1.8) : media ? entre(0.8, 1.1) : entre(0.3, 0.7),
      opacidade: brilhante ? entre(0.85, 1) : media ? entre(0.5, 0.75) : entre(0.2, 0.5),
      brilhante,
      cor: CORES[Math.floor(sorteio() * CORES.length)] ?? CORES[0]!,
    });
  }
  return estrelas;
}
