/** Respostas de exemplo da API, no formato do contrato, para os testes de interface. */
import type { AlertaDoPais, Mapa, Pais, PostoNoPainel, Visto } from "../servicos/api/cliente";

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

/** O visto de um país com dado (isento, 90 dias), com os campos que o teste quiser trocar. */
export function criarVisto(sobrescritas: Partial<Visto> = {}): Visto {
  return {
    situacao: "isento",
    motivo_outra_situacao: null,
    rotulo_original: "Visa not required",
    aceita_rg: false,
    varia_conforme_motivo: false,
    permanencia: { tipo: "padronizada", texto: "90 dias" },
    observacoes: [],
    origem: "proprio",
    soberano_nome: null,
    territorio_nome: null,
    dado_de: "2026-10-23T12:00:00Z",
    desatualizado: false,
    fonte: {
      nome: "Wikipédia: Visa requirements for Brazilian citizens",
      url: "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens",
      licenca: "CC BY-SA",
    },
    ...sobrescritas,
  };
}

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
  visto: criarVisto(),
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
      properties: {
        codigo: "US",
        tipo: "pais",
        soberano: null,
        titulo: "Estados Unidos",
        zoom: "US",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-125, 25],
            [-67, 25],
            [-67, 49],
            [-125, 49],
            [-125, 25],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: {
        codigo: "PR",
        tipo: "dependencia",
        soberano: "US",
        titulo: "Porto Rico",
        zoom: "PR",
      },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-67.3, 17.9],
            [-65.2, 17.9],
            [-65.2, 18.5],
            [-67.3, 18.5],
            [-67.3, 17.9],
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

/** /mapa com ícones: um grupo de dois postos (Washington), um país sem posto e a Líbia. */
export const MAPA_COM_POSTOS: Mapa = {
  ...MAPA_EXEMPLO,
  territorios: [
    ...MAPA_EXEMPLO.territorios,
    {
      codigo: "US",
      nome: "Estados Unidos",
      rotulo_busca: "Estados Unidos",
      termos_busca: [],
      tipo: "pais",
      soberano: null,
      bandeira: "US",
      identidade_do_soberano: false,
      nivel: "sem_alerta",
      regioes: [],
      observacao: null,
    },
    {
      codigo: "PR",
      nome: "Porto Rico (Estados Unidos)",
      rotulo_busca: "Porto Rico (Estados Unidos)",
      termos_busca: [],
      tipo: "dependencia",
      soberano: "US",
      bandeira: "PR",
      identidade_do_soberano: false,
      nivel: "sem_alerta",
      regioes: [],
      observacao: "Território dos Estados Unidos.",
    },
    {
      codigo: "LY",
      nome: "Líbia",
      rotulo_busca: "Líbia",
      termos_busca: [],
      tipo: "pais",
      soberano: null,
      bandeira: "LY",
      identidade_do_soberano: false,
      nivel: "nao_viajar",
      regioes: [],
      observacao: null,
    },
  ],
  postos: [
    ...MAPA_EXEMPLO.postos,
    {
      id: 89,
      territorio: "US",
      tipo: "Embaixada",
      cidade: "Washington",
      latitude: 38.9,
      longitude: -77,
      grupo: "38.9,-77",
    },
    {
      id: 90,
      territorio: "US",
      tipo: "Consulado-Geral",
      cidade: "Washington",
      latitude: 38.9,
      longitude: -77,
      grupo: "38.9,-77",
    },
    {
      id: 91,
      territorio: "US",
      tipo: "Consulado-Geral",
      cidade: "Miami",
      latitude: 25.76,
      longitude: -80.19,
      grupo: "25.76,-80.19",
    },
  ],
  paises_sem_posto: [
    { territorio: "PR", latitude: 18.2, longitude: -66.5, posto_responsavel_id: 91 },
    { territorio: "LY", latitude: 27, longitude: 17, posto_responsavel_id: null },
  ],
};

const POSTO_WASHINGTON = {
  ...POSTO_EXEMPLO,
  pais: "Estados Unidos",
  cidade: "Washington",
  grupo: "38.9,-77",
};

/** Painel dos Estados Unidos: dois postos na mesma cidade, que dividem o ícone. */
export const PAIS_COM_DOIS_POSTOS: Pais = criarPais({
  codigo: "US",
  nome: "Estados Unidos",
  bandeira: "US",
  postos: [
    { ...POSTO_WASHINGTON, id: 89, tipo: "Embaixada" },
    { ...POSTO_WASHINGTON, id: 90, tipo: "Consulado-Geral" },
  ],
});

/** Painel de Porto Rico: sem posto, atendido pelo consulado de Miami. */
export const PAIS_SEM_POSTO: Pais = criarPais({
  codigo: "PR",
  nome: "Porto Rico (Estados Unidos)",
  bandeira: "PR",
  tipo: "dependencia",
  soberano: "US",
  postos: [],
  posto_responsavel: {
    ...POSTO_EXEMPLO,
    id: 91,
    tipo: "Consulado-Geral",
    cidade: "Miami",
    pais: "Estados Unidos",
    grupo: "25.76,-80.19",
  },
});
