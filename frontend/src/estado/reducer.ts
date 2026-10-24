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

export type Acao = { tipo: "selecionar"; codigo: string } | { tipo: "limpar-selecao" };

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
  }
}
