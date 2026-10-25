import type { Mapa } from "../../servicos/api/cliente";

/**
 * Onde fica o posto responsável por um país sem posto (a linha tracejada do mapa e o
 * enquadramento, FR-018). Nulo para país com posto próprio e quando não há posto indicado.
 */
export function responsavelDe(
  mapa: Mapa,
  codigo: string,
): { latitude: number; longitude: number; grupo: string } | null {
  const idDoPosto = mapa.paises_sem_posto.find(
    (p) => p.territorio === codigo,
  )?.posto_responsavel_id;
  if (idDoPosto === null || idDoPosto === undefined) return null;
  const posto = mapa.postos.find((p) => p.id === idDoPosto);
  return posto === undefined
    ? null
    : { latitude: posto.latitude, longitude: posto.longitude, grupo: posto.grupo };
}
