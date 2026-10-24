import { useEffect, useState } from "react";
import type { Geometria } from "./feicoes";

export type EstadoDaGeometria =
  | { situacao: "carregando" }
  | { situacao: "erro"; mensagem: string }
  | { situacao: "pronto"; geometria: Geometria };

export const URL_DA_GEOMETRIA = `${import.meta.env.BASE_URL}geo/territorios.geojson`;

const TIPOS = ["pais", "dependencia", "neutro"];

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

/** O arquivo é nosso, mas vem da rede: confere a forma antes de entregar ao mapa. */
function validar(dados: unknown): Geometria {
  if (
    !ehObjeto(dados) ||
    dados["type"] !== "FeatureCollection" ||
    !Array.isArray(dados["features"])
  ) {
    throw new Error("Geometria inválida: não é uma coleção de feições");
  }
  for (const feicao of dados["features"] as unknown[]) {
    const propriedades = ehObjeto(feicao) ? feicao["properties"] : undefined;
    if (
      !ehObjeto(propriedades) ||
      typeof propriedades["codigo"] !== "string" ||
      typeof propriedades["tipo"] !== "string" ||
      !TIPOS.includes(propriedades["tipo"])
    ) {
      throw new Error("Geometria inválida: feição sem código ou tipo");
    }
  }
  return dados as unknown as Geometria;
}

const carregamentos = new Map<string, Promise<Geometria>>();

/** Para os testes: esquece a geometria já carregada. */
export function limparCacheDaGeometria(): void {
  carregamentos.clear();
}

function carregar(buscar: typeof fetch, url: string): Promise<Geometria> {
  const existente = carregamentos.get(url);
  if (existente) return existente;
  const carregamento = buscar(url)
    .then(async (resposta) => {
      if (!resposta.ok) throw new Error(`Erro ${resposta.status} ao carregar a geometria`);
      return validar(await resposta.json());
    })
    .catch((erro: unknown) => {
      carregamentos.delete(url); // permite tentar de novo depois
      throw erro;
    });
  carregamentos.set(url, carregamento);
  return carregamento;
}

/** Carrega o arquivo de geometria uma única vez, qualquer que seja o número de usuários do hook. */
export function useGeometria(
  buscar: typeof fetch = (...argumentos) => fetch(...argumentos),
  url: string = URL_DA_GEOMETRIA,
): EstadoDaGeometria {
  const [estado, setEstado] = useState<EstadoDaGeometria>({ situacao: "carregando" });

  useEffect(() => {
    let ativo = true;
    carregar(buscar, url).then(
      (geometria) => ativo && setEstado({ situacao: "pronto", geometria }),
      (erro: unknown) =>
        ativo &&
        setEstado({
          situacao: "erro",
          mensagem: erro instanceof Error ? erro.message : "Não foi possível carregar o mapa",
        }),
    );
    return () => {
      ativo = false;
    };
  }, [buscar, url]);

  return estado;
}
