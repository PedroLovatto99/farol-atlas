/** Respostas de exemplo da API, no formato do contrato, para os testes de interface. */
import type { AlertaDoPais, Mapa, Pais, PostoNoPainel } from "../servicos/api/cliente";

export const MAPA_EXEMPLO: Mapa = {
  dados_obtidos: true,
  atualizado_em: "2026-10-23T12:00:00Z",
  desatualizado: false,
  territorios: [
    {
      codigo: "DK",
      nome: "Dinamarca",
      rotulo_busca: "Dinamarca",
      termos_busca: [],
      tipo: "pais",
      soberano: null,
      bandeira: "DK",
      identidade_do_soberano: false,
      nivel: "sem_alerta",
      regioes: [],
      observacao: null,
    },
    {
      codigo: "LB",
      nome: "Líbano",
      rotulo_busca: "Líbano",
      termos_busca: [],
      tipo: "pais",
      soberano: null,
      bandeira: "LB",
      identidade_do_soberano: false,
      nivel: "evitar",
      regioes: [{ nome: "Sul do Líbano", nivel: "nao_viajar" }],
      observacao: null,
    },
    {
      codigo: "BO",
      nome: "Bolívia",
      rotulo_busca: "Bolívia",
      termos_busca: [],
      tipo: "pais",
      soberano: null,
      bandeira: "BO",
      identidade_do_soberano: false,
      nivel: "nao_verificado",
      regioes: [],
      observacao: null,
    },
    {
      codigo: "GL",
      nome: "Groenlândia (Dinamarca)",
      rotulo_busca: "Groenlândia (Dinamarca)",
      termos_busca: [],
      tipo: "dependencia",
      soberano: "DK",
      bandeira: "GL",
      identidade_do_soberano: false,
      nivel: "sem_alerta",
      regioes: [],
      observacao: "Território da Dinamarca.",
    },
    {
      codigo: "XK",
      nome: "Sérvia",
      rotulo_busca: "Kosovo (Sérvia)",
      termos_busca: ["Kosovo"],
      tipo: "dependencia",
      soberano: "RS",
      bandeira: "RS",
      identidade_do_soberano: true,
      nivel: "sem_alerta",
      regioes: [],
      observacao: "Kosovo: o Brasil não reconhece a independência.",
    },
  ],
  postos: [
    {
      id: 1,
      territorio: "DK",
      tipo: "Embaixada",
      cidade: "Copenhague",
      latitude: 55.6761,
      longitude: 12.5683,
      grupo: "55.6761,12.5683",
    },
  ],
  paises_sem_posto: [],
};

export const POSTO_EXEMPLO: PostoNoPainel = {
  id: 1,
  tipo: "Embaixada",
  cidade: "Copenhague",
  pais: "Dinamarca",
  grupo: "55.6761,12.5683",
  endereco: null,
  telefone_plantao: null,
  contato_coletado_em: null,
  contato_fonte_url: null,
};

export const PAIS_EXEMPLO: Pais = {
  codigo: "DK",
  nome: "Dinamarca",
  tipo: "pais",
  soberano: null,
  bandeira: "DK",
  identidade_do_soberano: false,
  nivel: "sem_alerta",
  regioes: [],
  observacao: null,
  observacao_no_topo: false,
  eh_brasil: false,
  alertas: [],
  postos: [POSTO_EXEMPLO],
  posto_responsavel: null,
  sem_posto_indicado: false,
  fonte_postos: {
    conferido_em: "2026-10-21",
    fontes: [
      {
        nome: "Itamaraty",
        url: "https://www.gov.br/mre/pt-br/assuntos/portal-consular/reparticoes-consulares-do-brasil",
        licenca: null,
      },
      {
        nome: "Wikipédia",
        url: "https://en.wikipedia.org/wiki/List_of_diplomatic_missions_of_Brazil",
        licenca: "CC BY-SA",
      },
    ],
  },
};

export const ALERTA_EXEMPLO: AlertaDoPais = {
  titulo: "Alerta de viagem – Dinamarca",
  url: "https://www.gov.br/mre/pt-br/alertas/dinamarca",
  publicado_em: "2026-08-17T15:00:00Z",
  modificado_em: null,
  define_nivel: true,
  situacao_normalizada: false,
};

/** Um painel de país, com os campos que o teste quiser trocar. */
export function criarPais(sobrescritas: Partial<Pais> = {}): Pais {
  return { ...PAIS_EXEMPLO, ...sobrescritas };
}

export function criarPosto(sobrescritas: Partial<PostoNoPainel> = {}): PostoNoPainel {
  return { ...POSTO_EXEMPLO, ...sobrescritas };
}

/** Geometria mínima para os testes da tela (cada território é um retângulo). */
export const GEOMETRIA_EXEMPLO = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { codigo: "DK", tipo: "pais", soberano: null, titulo: "Dinamarca", zoom: "DK" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [8, 54.5],
            [15, 54.5],
            [15, 57.8],
            [8, 57.8],
            [8, 54.5],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: { codigo: "RS", tipo: "pais", soberano: null, titulo: "Sérvia", zoom: "RS" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [18.8, 42.2],
            [23, 42.2],
            [23, 46.2],
            [18.8, 46.2],
            [18.8, 42.2],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        codigo: "XK",
        tipo: "dependencia",
        soberano: "RS",
        titulo: "Kosovo",
        zoom: "RS",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [20, 42.3],
            [21.8, 42.3],
            [21.8, 43.3],
            [20, 43.3],
            [20, 42.3],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: { codigo: "EH", tipo: "neutro", soberano: null, titulo: "Saara", zoom: null },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-17, 20],
            [-8.7, 20],
            [-8.7, 27.7],
            [-17, 27.7],
            [-17, 20],
          ],
        ],
      },
    },
  ],
} as const;
