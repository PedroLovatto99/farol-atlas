/** Níveis de alerta exibidos no mapa (FR-001), com rótulo, texto explicativo e cor. */

export type NivelId = "sem_alerta" | "evitar" | "nao_viajar" | "nao_verificado";

export interface InfoDoNivel {
  rotulo: string;
  texto: string;
  /** Maior = mais grave. "Não verificado" fica abaixo de todos. */
  gravidade: number;
  /** Mesma cor do token em tema.css (um teste confere); o MapLibre precisa do valor em hex. */
  cor: string;
}

export const NIVEIS: Readonly<Record<NivelId, InfoDoNivel>> = {
  sem_alerta: {
    rotulo: "Sem alerta do Itamaraty",
    texto:
      "O Itamaraty não publicou alerta de viagem para este país. " +
      "Isso não significa que o governo recomenda a viagem.",
    gravidade: 0,
    cor: "#C0DD97",
  },
  evitar: {
    rotulo: "Evite viagens não essenciais",
    texto: "O Itamaraty recomenda evitar viagens não essenciais a este país.",
    gravidade: 1,
    cor: "#FAC775",
  },
  nao_viajar: {
    rotulo: "Não viaje",
    texto: "O Itamaraty recomenda não viajar a este país.",
    gravidade: 2,
    cor: "#E24B4A",
  },
  nao_verificado: {
    rotulo: "Não verificado",
    texto: "Ainda não temos informação confirmada do Itamaraty sobre este país.",
    gravidade: -1,
    cor: "#D3D1C7",
  },
};

/** Sem dado confirmado, o padrão nunca é o estado mais favorável (princípio V). */
export const NIVEL_PADRAO: NivelId = "nao_verificado";

export const ORDEM_DA_LEGENDA: readonly NivelId[] = [
  "sem_alerta",
  "evitar",
  "nao_viajar",
  "nao_verificado",
];

export function nivelMaisGrave(niveis: readonly NivelId[]): NivelId {
  let maisGrave: NivelId = NIVEL_PADRAO;
  for (const nivel of niveis) {
    if (NIVEIS[nivel].gravidade > NIVEIS[maisGrave].gravidade) {
      maisGrave = nivel;
    }
  }
  return maisGrave;
}
