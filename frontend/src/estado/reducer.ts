/** Estado compartilhado da aplicação (sem biblioteca global): seleção, postos e filtro de níveis. */
import { ORDEM_DA_LEGENDA, type NivelId } from "../compartilhado/niveis";
import { TODAS_AS_CHAVES_DE_VISTO, type ChaveDeVisto } from "../compartilhado/vistos";
import { alternarNivel } from "../funcionalidades/legenda/filtro";
import { alternarVisto } from "../funcionalidades/legenda/filtroDeVistos";
import type { ModoDoGlobo } from "../funcionalidades/mapa/tipos";
import type { VistosDoMapa } from "../servicos/api/cliente";

/** Os vistos do globo (`GET /vistos`), pedidos só quando a pessoa escolhe o modo "Vistos". */
export type EstadoDosVistos =
  | { situacao: "nao_pedido" }
  | { situacao: "carregando" }
  | { situacao: "erro"; mensagem: string }
  | { situacao: "pronto"; dados: VistosDoMapa };

export interface Estado {
  /** Código do território selecionado (inclusive Kosovo e Malvinas, que abrem o painel do soberano). */
  selecionado: string | null;
  /** Ids dos postos expandidos no painel. */
  postosExpandidos: readonly number[];
  /** Ícone em destaque no mapa (FR-018a). */
  grupoEmDestaque: string | null;
  /** Níveis marcados na legenda; todos vêm marcados ao abrir o site (FR-024). */
  niveisMarcados: readonly NivelId[];
  /** O que o globo mostra; sempre "alertas" ao abrir e nunca guardado entre visitas (FR-021). */
  modo: ModoDoGlobo;
  /** Chaves marcadas na legenda de vistos; todas ao abrir; independente de `niveisMarcados`. */
  vistosMarcados: readonly ChaveDeVisto[];
  vistos: EstadoDosVistos;
}

export type Acao =
  | { tipo: "selecionar"; codigo: string }
  | { tipo: "limpar-selecao" }
  /** Expandir um posto no painel põe o ícone dele em destaque, e só ele (FR-018a, FR-018b). */
  | { tipo: "expandir-posto"; id: number; grupo: string }
  /** Recolher o posto em destaque tira o destaque (FR-018b). */
  | { tipo: "recolher-posto"; id: number; grupo: string }
  /** Tocar num ícone abre o painel do país com os postos do ícone já expandidos (FR-018g). */
  | { tipo: "tocar-icone"; territorio: string; grupo: string; ids: readonly number[] }
  /** Marca ou desmarca um nível na legenda; não mexe na seleção nem nos postos (FR-024). */
  | { tipo: "alternar-nivel"; nivel: NivelId }
  /** O botão da mensagem "nenhum nível marcado". */
  | { tipo: "marcar-todos-niveis" }
  /** Alterna o globo entre "Alertas" e "Vistos"; não mexe em seleção, painel, postos nem câmera. */
  | { tipo: "trocar-modo"; modo: ModoDoGlobo }
  /** Marca ou desmarca uma chave da legenda de vistos (o item "Isento" leva o subitem do RG). */
  | { tipo: "alternar-visto"; chave: ChaveDeVisto }
  | { tipo: "marcar-todos-vistos" }
  | { tipo: "vistos-carregando" }
  | { tipo: "vistos-carregados"; dados: VistosDoMapa }
  | { tipo: "vistos-falhou"; mensagem: string };

export const ESTADO_INICIAL: Estado = {
  selecionado: null,
  postosExpandidos: [],
  grupoEmDestaque: null,
  niveisMarcados: ORDEM_DA_LEGENDA,
  modo: "alertas",
  vistosMarcados: TODAS_AS_CHAVES_DE_VISTO,
  vistos: { situacao: "nao_pedido" },
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
    case "alternar-nivel":
      return { ...estado, niveisMarcados: alternarNivel(estado.niveisMarcados, acao.nivel) };
    case "marcar-todos-niveis":
      if (ORDEM_DA_LEGENDA.every((n) => estado.niveisMarcados.includes(n))) return estado;
      return { ...estado, niveisMarcados: ORDEM_DA_LEGENDA };
    case "trocar-modo":
      return acao.modo === estado.modo ? estado : { ...estado, modo: acao.modo };
    case "alternar-visto":
      return { ...estado, vistosMarcados: alternarVisto(estado.vistosMarcados, acao.chave) };
    case "marcar-todos-vistos":
      if (TODAS_AS_CHAVES_DE_VISTO.every((c) => estado.vistosMarcados.includes(c))) return estado;
      return { ...estado, vistosMarcados: TODAS_AS_CHAVES_DE_VISTO };
    case "vistos-carregando":
      return { ...estado, vistos: { situacao: "carregando" } };
    case "vistos-carregados":
      return { ...estado, vistos: { situacao: "pronto", dados: acao.dados } };
    case "vistos-falhou":
      return { ...estado, vistos: { situacao: "erro", mensagem: acao.mensagem } };
  }
}
