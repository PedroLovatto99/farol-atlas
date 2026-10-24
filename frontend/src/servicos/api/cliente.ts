/**
 * Cliente tipado da API. Toda resposta é validada em tempo de execução: o que chega da rede é
 * `unknown` até provar que tem a forma esperada (princípio I: nada de `any`).
 */
import type { components } from "./esquema";

type Esquemas = components["schemas"];

export type Mapa = Esquemas["Mapa"];
export type TerritorioNoMapa = Esquemas["TerritorioNoMapa"];
export type PostoNoMapa = Esquemas["PostoNoMapa"];
export type PaisSemPosto = Esquemas["PaisSemPosto"];
export type Pais = Esquemas["Pais"];
export type AlertaDoPais = Esquemas["AlertaDoPais"];
export type PostoNoPainel = Esquemas["PostoNoPainel"];
export type FontePostos = Esquemas["FontePostos"];
export type Regiao = Esquemas["Regiao"];
export type Saude = Esquemas["Saude"];
export type Nivel = Esquemas["Nivel"];
export type TipoPosto = Esquemas["TipoPosto"];

export class ErroDeApi extends Error {
  readonly status: number;

  constructor(status: number, mensagem: string) {
    super(mensagem);
    this.name = "ErroDeApi";
    this.status = status;
  }
}

// --------------------------------------------------------------------------- validação
type Objeto = Record<string, unknown>;

function invalido(campo: string, status: number): never {
  throw new ErroDeApi(status, `Resposta inválida da API (campo "${campo}")`);
}

function ehObjeto(valor: unknown): valor is Objeto {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

class Leitor {
  constructor(
    private readonly origem: Objeto,
    private readonly caminho: string,
    private readonly status: number,
  ) {}

  private falhar(campo: string): never {
    return invalido(`${this.caminho}${campo}`, this.status);
  }

  texto(campo: string): string {
    const valor = this.origem[campo];
    return typeof valor === "string" ? valor : this.falhar(campo);
  }

  textoOuNulo(campo: string): string | null {
    const valor = this.origem[campo];
    if (valor === null) return null;
    return typeof valor === "string" ? valor : this.falhar(campo);
  }

  numero(campo: string): number {
    const valor = this.origem[campo];
    return typeof valor === "number" && Number.isFinite(valor) ? valor : this.falhar(campo);
  }

  numeroOuNulo(campo: string): number | null {
    const valor = this.origem[campo];
    if (valor === null) return null;
    return typeof valor === "number" && Number.isFinite(valor) ? valor : this.falhar(campo);
  }

  booleano(campo: string): boolean {
    const valor = this.origem[campo];
    return typeof valor === "boolean" ? valor : this.falhar(campo);
  }

  booleanoOpcional(campo: string): boolean | undefined {
    const valor = this.origem[campo];
    if (valor === undefined) return undefined;
    return typeof valor === "boolean" ? valor : this.falhar(campo);
  }

  um<T extends string>(campo: string, permitidos: readonly T[]): T {
    const valor = this.origem[campo];
    const encontrado = permitidos.find((p) => p === valor);
    return encontrado ?? this.falhar(campo);
  }

  lista<T>(campo: string, ler: (item: Leitor) => T): T[] {
    const valor = this.origem[campo];
    if (!Array.isArray(valor)) return this.falhar(campo);
    return valor.map((item: unknown, indice) => {
      if (!ehObjeto(item)) return this.falhar(`${campo}[${indice}]`);
      return ler(new Leitor(item, `${this.caminho}${campo}[${indice}].`, this.status));
    });
  }

  listaDeTextos(campo: string): string[] {
    const valor = this.origem[campo];
    if (!Array.isArray(valor) || !valor.every((item) => typeof item === "string")) {
      return this.falhar(campo);
    }
    return valor.map(String);
  }

  objetoOuNulo<T>(campo: string, ler: (item: Leitor) => T): T | null {
    const valor = this.origem[campo];
    if (valor === null) return null;
    if (!ehObjeto(valor)) return this.falhar(campo);
    return ler(new Leitor(valor, `${this.caminho}${campo}.`, this.status));
  }
}

function raiz(dados: unknown, status: number): Leitor {
  if (!ehObjeto(dados)) return invalido("(raiz)", status);
  return new Leitor(dados, "", status);
}

const NIVEIS = ["sem_alerta", "evitar", "nao_viajar", "nao_verificado"] as const;
const NIVEIS_REGIONAIS = ["evitar", "nao_viajar"] as const;
const TIPOS_DE_TERRITORIO = ["pais", "dependencia"] as const;
const TIPOS_DE_POSTO = [
  "Embaixada",
  "Consulado-Geral",
  "Consulado",
  "Vice-Consulado",
  "Escritório de Representação",
  "Escritório Comercial",
] as const;

function lerRegiao(l: Leitor): Regiao {
  return { nome: l.texto("nome"), nivel: l.um("nivel", NIVEIS_REGIONAIS) };
}

function lerTerritorio(l: Leitor): TerritorioNoMapa {
  return {
    codigo: l.texto("codigo"),
    nome: l.texto("nome"),
    rotulo_busca: l.texto("rotulo_busca"),
    termos_busca: l.listaDeTextos("termos_busca"),
    tipo: l.um("tipo", TIPOS_DE_TERRITORIO),
    soberano: l.textoOuNulo("soberano"),
    bandeira: l.textoOuNulo("bandeira"),
    identidade_do_soberano: l.booleano("identidade_do_soberano"),
    nivel: l.um("nivel", NIVEIS),
    regioes: l.lista("regioes", lerRegiao),
    observacao: l.textoOuNulo("observacao"),
  };
}

function lerPostoDoMapa(l: Leitor): PostoNoMapa {
  return {
    id: l.numero("id"),
    territorio: l.texto("territorio"),
    tipo: l.um("tipo", TIPOS_DE_POSTO),
    cidade: l.texto("cidade"),
    latitude: l.numero("latitude"),
    longitude: l.numero("longitude"),
    grupo: l.texto("grupo"),
  };
}

function lerPaisSemPosto(l: Leitor): PaisSemPosto {
  return {
    territorio: l.texto("territorio"),
    latitude: l.numero("latitude"),
    longitude: l.numero("longitude"),
    posto_responsavel_id: l.numeroOuNulo("posto_responsavel_id"),
  };
}

export function validarMapa(dados: unknown, status = 200): Mapa {
  const l = raiz(dados, status);
  return {
    dados_obtidos: l.booleano("dados_obtidos"),
    atualizado_em: l.textoOuNulo("atualizado_em"),
    desatualizado: l.booleano("desatualizado"),
    territorios: l.lista("territorios", lerTerritorio),
    postos: l.lista("postos", lerPostoDoMapa),
    paises_sem_posto: l.lista("paises_sem_posto", lerPaisSemPosto),
  };
}

function lerAlerta(l: Leitor): AlertaDoPais {
  const pendente = l.booleanoOpcional("pendente");
  return {
    titulo: l.texto("titulo"),
    url: l.texto("url"),
    publicado_em: l.texto("publicado_em"),
    modificado_em: l.textoOuNulo("modificado_em"),
    define_nivel: l.booleano("define_nivel"),
    situacao_normalizada: l.booleano("situacao_normalizada"),
    ...(pendente === undefined ? {} : { pendente }),
  };
}

function lerPostoDoPainel(l: Leitor): PostoNoPainel {
  return {
    id: l.numero("id"),
    tipo: l.um("tipo", TIPOS_DE_POSTO),
    cidade: l.texto("cidade"),
    pais: l.texto("pais"),
    grupo: l.texto("grupo"),
    endereco: l.textoOuNulo("endereco"),
    telefone_plantao: l.textoOuNulo("telefone_plantao"),
    contato_coletado_em: l.textoOuNulo("contato_coletado_em"),
    contato_fonte_url: l.textoOuNulo("contato_fonte_url"),
  };
}

function lerFonte(l: Leitor): FontePostos {
  return {
    conferido_em: l.texto("conferido_em"),
    fontes: l.lista("fontes", (f) => ({
      nome: f.texto("nome"),
      url: f.texto("url"),
      licenca: f.textoOuNulo("licenca"),
    })),
  };
}

export function validarPais(dados: unknown, status = 200): Pais {
  const l = raiz(dados, status);
  const unica = l.booleanoOpcional("regiao_unica_do_alerta");
  return {
    codigo: l.texto("codigo"),
    nome: l.texto("nome"),
    tipo: l.um("tipo", TIPOS_DE_TERRITORIO),
    soberano: l.textoOuNulo("soberano"),
    bandeira: l.textoOuNulo("bandeira"),
    identidade_do_soberano: l.booleano("identidade_do_soberano"),
    nivel: l.um("nivel", NIVEIS),
    regioes: l.lista("regioes", lerRegiao),
    ...(unica === undefined ? {} : { regiao_unica_do_alerta: unica }),
    observacao: l.textoOuNulo("observacao"),
    observacao_no_topo: l.booleano("observacao_no_topo"),
    eh_brasil: l.booleano("eh_brasil"),
    alertas: l.lista("alertas", lerAlerta),
    postos: l.lista("postos", lerPostoDoPainel),
    posto_responsavel: l.objetoOuNulo("posto_responsavel", lerPostoDoPainel),
    sem_posto_indicado: l.booleano("sem_posto_indicado"),
    fonte_postos: l.objetoOuNulo("fonte_postos", lerFonte),
  };
}

export function validarSaude(dados: unknown, status = 200): Saude {
  const l = raiz(dados, status);
  return {
    banco: l.um("banco", ["ok", "falha"] as const),
    ultima_coleta_completa_em: l.textoOuNulo("ultima_coleta_completa_em"),
    ultima_tentativa_em: l.textoOuNulo("ultima_tentativa_em"),
    alertas_pendentes: l.numero("alertas_pendentes"),
  };
}

// --------------------------------------------------------------------------- cliente
export interface ClienteDaApi {
  obterMapa(sinal?: AbortSignal): Promise<Mapa>;
  obterPais(codigo: string, sinal?: AbortSignal): Promise<Pais>;
  obterSaude(sinal?: AbortSignal): Promise<Saude>;
}

async function detalheDoErro(resposta: Response): Promise<string> {
  try {
    const corpo: unknown = await resposta.json();
    if (ehObjeto(corpo) && typeof corpo["detalhe"] === "string") return corpo["detalhe"];
  } catch {
    // corpo que não é JSON: cai na mensagem padrão
  }
  return `Erro ${resposta.status} ao falar com a API`;
}

export function criarCliente(
  base: string = import.meta.env.VITE_API_URL ?? "",
  buscar: typeof fetch = (...argumentos) => fetch(...argumentos),
): ClienteDaApi {
  const prefixo = `${base.replace(/\/+$/, "")}/api/v1`;

  async function pedir<T>(
    caminho: string,
    validar: (dados: unknown, status: number) => T,
    sinal?: AbortSignal,
  ): Promise<T> {
    let resposta: Response;
    try {
      resposta = await buscar(`${prefixo}${caminho}`, { method: "GET", signal: sinal ?? null });
    } catch (erro) {
      if (erro instanceof DOMException && erro.name === "AbortError") throw erro;
      throw new ErroDeApi(0, "Não foi possível falar com o servidor");
    }
    if (!resposta.ok) {
      throw new ErroDeApi(resposta.status, await detalheDoErro(resposta));
    }
    let dados: unknown;
    try {
      dados = await resposta.json();
    } catch {
      throw new ErroDeApi(resposta.status, "Resposta inválida da API (não é JSON)");
    }
    return validar(dados, resposta.status);
  }

  return {
    obterMapa: (sinal) => pedir("/mapa", validarMapa, sinal),
    obterPais: (codigo, sinal) =>
      pedir(`/paises/${encodeURIComponent(codigo)}`, validarPais, sinal),
    obterSaude: (sinal) => pedir("/saude", validarSaude, sinal),
  };
}
