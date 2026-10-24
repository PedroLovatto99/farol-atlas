/** API simulada para os testes de interface: um cliente que responde com dados de exemplo. */
import { vi } from "vitest";
import { ErroDeApi, type ClienteDaApi, type Mapa, type Pais } from "../servicos/api/cliente";
import { MAPA_EXEMPLO, PAIS_EXEMPLO } from "./dados-exemplo";

export interface RespostasSimuladas {
  mapa?: Mapa | ErroDeApi;
  paises?: Readonly<Record<string, Pais | ErroDeApi>>;
}

export function criarApiSimulada(respostas: RespostasSimuladas = {}) {
  const mapa = respostas.mapa ?? MAPA_EXEMPLO;
  const paises = respostas.paises ?? { [PAIS_EXEMPLO.codigo]: PAIS_EXEMPLO };

  const obterMapa = vi.fn<ClienteDaApi["obterMapa"]>(() =>
    mapa instanceof ErroDeApi ? Promise.reject(mapa) : Promise.resolve(mapa),
  );
  const obterPais = vi.fn<ClienteDaApi["obterPais"]>((codigo) => {
    const pais = paises[codigo];
    if (pais === undefined) return Promise.reject(new ErroDeApi(404, "Território não encontrado"));
    return pais instanceof ErroDeApi ? Promise.reject(pais) : Promise.resolve(pais);
  });
  const obterSaude = vi.fn<ClienteDaApi["obterSaude"]>(() =>
    Promise.resolve({
      banco: "ok",
      ultima_coleta_completa_em: null,
      ultima_tentativa_em: null,
      alertas_pendentes: 0,
    }),
  );

  const cliente: ClienteDaApi = { obterMapa, obterPais, obterSaude };
  return { cliente, obterMapa, obterPais, obterSaude };
}
