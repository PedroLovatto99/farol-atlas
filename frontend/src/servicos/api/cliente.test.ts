import { describe, expect, it, vi } from "vitest";
import { ErroDeApi, criarCliente } from "./cliente";

const MAPA_VALIDO = {
  dados_obtidos: true,
  atualizado_em: "2026-10-23T12:00:00Z",
  desatualizado: false,
  territorios: [
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
  ],
  postos: [],
  paises_sem_posto: [],
};

const PAIS_VALIDO = {
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
  postos: [],
  posto_responsavel: null,
  sem_posto_indicado: false,
  fonte_postos: null,
};

function respostaJson(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function clienteCom(resposta: Response | Error, base = "http://api.exemplo") {
  const fetchFalso = vi.fn<typeof fetch>(() =>
    resposta instanceof Error ? Promise.reject(resposta) : Promise.resolve(resposta),
  );
  return { cliente: criarCliente(base, fetchFalso), fetchFalso };
}

describe("cliente da API", () => {
  it("obterMapa faz uma única chamada GET e devolve o mapa tipado", async () => {
    const { cliente, fetchFalso } = clienteCom(respostaJson(MAPA_VALIDO));
    const mapa = await cliente.obterMapa();
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api.exemplo/api/v1/mapa");
    expect(mapa.territorios[0]?.regioes[0]?.nome).toBe("Sul do Líbano");
  });

  it("ignora a barra final da base", async () => {
    const { cliente, fetchFalso } = clienteCom(respostaJson(MAPA_VALIDO), "http://api.exemplo/");
    await cliente.obterMapa();
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api.exemplo/api/v1/mapa");
  });

  it("obterPais chama /paises/{codigo}", async () => {
    const { cliente, fetchFalso } = clienteCom(respostaJson(PAIS_VALIDO));
    const pais = await cliente.obterPais("DK");
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api.exemplo/api/v1/paises/DK");
    expect(pais.nome).toBe("Dinamarca");
  });

  it("repassa o sinal de cancelamento ao fetch", async () => {
    const { cliente, fetchFalso } = clienteCom(respostaJson(PAIS_VALIDO));
    const controle = new AbortController();
    await cliente.obterPais("DK", controle.signal);
    expect(fetchFalso.mock.calls[0]?.[1]?.signal).toBe(controle.signal);
  });

  it("obterSaude devolve o estado do banco e da coleta", async () => {
    const corpo = {
      banco: "ok",
      ultima_coleta_completa_em: null,
      ultima_tentativa_em: null,
      alertas_pendentes: 0,
    };
    const { cliente } = clienteCom(respostaJson(corpo));
    expect((await cliente.obterSaude()).banco).toBe("ok");
  });

  it("erro HTTP vira ErroDeApi com o status e o detalhe da API", async () => {
    const { cliente } = clienteCom(respostaJson({ detalhe: "Território não encontrado" }, 404));
    const erro = await cliente.obterPais("ZZ").catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroDeApi);
    expect((erro as ErroDeApi).status).toBe(404);
    expect((erro as ErroDeApi).message).toBe("Território não encontrado");
  });

  it("erro HTTP sem JSON também vira ErroDeApi", async () => {
    const { cliente } = clienteCom(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(cliente.obterMapa()).rejects.toMatchObject({ status: 502 });
  });

  it("falha de rede vira ErroDeApi com status 0", async () => {
    const { cliente } = clienteCom(new TypeError("Failed to fetch"));
    await expect(cliente.obterMapa()).rejects.toMatchObject({ status: 0 });
  });

  it("resposta com forma inválida não passa (nível desconhecido)", async () => {
    const invalido = {
      ...MAPA_VALIDO,
      territorios: [{ ...MAPA_VALIDO.territorios[0], nivel: "tudo_bem" }],
    };
    const { cliente } = clienteCom(respostaJson(invalido));
    await expect(cliente.obterMapa()).rejects.toThrow(/inválida/i);
  });

  it("resposta com campo obrigatório faltando não passa", async () => {
    const { dados_obtidos: _removido, ...semCampo } = MAPA_VALIDO;
    const { cliente } = clienteCom(respostaJson(semCampo));
    await expect(cliente.obterMapa()).rejects.toThrow(/inválida/i);
  });

  it("resposta que não é um objeto não passa", async () => {
    const { cliente } = clienteCom(respostaJson([1, 2, 3]));
    await expect(cliente.obterPais("DK")).rejects.toThrow(/inválida/i);
  });
});
