/** Estado compartilhado da aplicação (sem biblioteca global): seleção, postos e filtro de níveis. */
import { ORDEM_DA_LEGENDA, type NivelId } from "../compartilhado/niveis";

export interface Estado {
  /** Código do território selecionado (inclusive Kosovo e Malvinas, que abrem o painel do soberano). */
  selecionado: string | null;
  /** Ids dos postos expandidos no painel. */
  postosExpandidos: readonly number[];
  /** Ícone em destaque no mapa (FR-018a). */
  grupoEmDestaque: string | null;
  /** Níveis marcados na legenda; todos vêm marcados ao abrir o site (FR-024). */
  niveisMarcados: readonly NivelId[];
}

export type Acao =
  | { tipo: "selecionar"; codigo: string }
  | { tipo: "limpar-selecao" }
  /** Expandir um posto no painel põe o ícone dele em destaque, e só ele (FR-018a, FR-018b). */
  | { tipo: "expandir-posto"; id: number; grupo: string }
  /** Recolher o posto em destaque tira o destaque (FR-018b). */
  | { tipo: "recolher-posto"; id: number; grupo: string }
  /** Tocar num ícone abre o painel do país com os postos do ícone já expandidos (FR-018g). */
  | { tipo: "tocar-icone"; territorio: string; grupo: string; ids: readonly number[] };

export const ESTADO_INICIAL: Estado = {
  selecionado: null,
  postosExpandidos: [],
  grupoEmDestaque: null,
  niveisMarcados: ORDEM_DA_LEGENDA,
};

export function reducer(estado: Estado, acao: Acao): Estado {
  switch (acao.tipo) {
    case "selecionar":
      return { ...estado, selecionado: acao.codigo, postosExpandidos: [], grupoEmDestaque: null };
    case "limpar-selecao":
      return { ...estado, selecionado: null, postosExpandidos: [], grupoEmDestaque: null };
    case "expandir-posto":
      // O navegador repete o evento ao abrir por código: nada a mudar, nem uma renderização
      if (estado.postosExpandidos.includes(acao.id) && estado.grupoEmDestaque === acao.grupo) {
        return estado;
      }
      return {
        ...estado,
        postosExpandidos: estado.postosExpandidos.includes(acao.id)
          ? estado.postosExpandidos
          : [...estado.postosExpandidos, acao.id],
        grupoEmDestaque: acao.grupo,
      };
    case "recolher-posto": {
      const aberto = estado.postosExpandidos.includes(acao.id);
      const emDestaque = estado.grupoEmDestaque === acao.grupo;
      if (!aberto && !emDestaque) return estado;
      return {
        ...estado,
        postosExpandidos: estado.postosExpandidos.filter((id) => id !== acao.id),
        grupoEmDestaque: emDestaque ? null : estado.grupoEmDestaque,
      };
    }
    case "tocar-icone":
      return {
        ...estado,
        selecionado: acao.territorio,
        postosExpandidos: acao.ids,
        grupoEmDestaque: acao.grupo,
      };
  }
}
