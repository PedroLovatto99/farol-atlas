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
  visto: null,
};

const VISTO_VALIDO = {
  situacao: "isento",
  motivo_outra_situacao: null,
  rotulo_original: "Visa not required",
  aceita_rg: false,
  varia_conforme_motivo: false,
  permanencia: { tipo: "padronizada", texto: "90 dias" },
  observacoes: [{ texto_original: "Passport required.", traducao: "Passaporte necessário." }],
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
};

const VISTO_SEM_INFORMACAO = {
  ...VISTO_VALIDO,
  situacao: "sem_informacao",
  rotulo_original: null,
  permanencia: null,
  observacoes: [],
  origem: null,
  dado_de: null,
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
  describe("visto do país (feature 002)", () => {
    async function lerPais(corpo: unknown) {
      const { cliente } = clienteCom(respostaJson(corpo));
      return cliente.obterPais("DK");
    }

    it("aceita o visto como objeto, com permanência e observações", async () => {
      const pais = await lerPais({ ...PAIS_VALIDO, visto: VISTO_VALIDO });
      expect(pais.visto?.situacao).toBe("isento");
      expect(pais.visto?.permanencia).toEqual({ tipo: "padronizada", texto: "90 dias" });
      expect(pais.visto?.observacoes[0]?.traducao).toBe("Passaporte necessário.");
      expect(pais.visto?.fonte.licenca).toBe("CC BY-SA");
    });

    it("aceita o visto nulo (o Brasil)", async () => {
      expect((await lerPais({ ...PAIS_VALIDO, visto: null })).visto).toBeNull();
    });

    it("aceita o estado explícito de sem informação", async () => {
      const pais = await lerPais({ ...PAIS_VALIDO, visto: VISTO_SEM_INFORMACAO });
      expect(pais.visto?.situacao).toBe("sem_informacao");
      expect(pais.visto?.dado_de).toBeNull();
    });

    it("aceita a entrada herdada do soberano", async () => {
      const herdado = { ...VISTO_VALIDO, origem: "soberano", soberano_nome: "Reino Unido" };
      const pais = await lerPais({ ...PAIS_VALIDO, visto: herdado });
      expect(pais.visto?.soberano_nome).toBe("Reino Unido");
    });

    it("aceita o nome do território a que o visto se refere (Kosovo, Ilhas Malvinas)", async () => {
      const malvinas = { ...VISTO_VALIDO, territorio_nome: "Ilhas Malvinas" };
      const pais = await lerPais({ ...PAIS_VALIDO, visto: malvinas });
      expect(pais.visto?.territorio_nome).toBe("Ilhas Malvinas");
      expect(pais.visto?.aceita_rg).toBe(false);
    });

    it("sem territorio_nome (nulo é diferente de ausente) a resposta não passa", async () => {
      const { territorio_nome: _removido, ...semNome } = VISTO_VALIDO;
      await expect(lerPais({ ...PAIS_VALIDO, visto: semNome })).rejects.toThrow(/territorio_nome/);
    });

    it("sem o campo visto a resposta não passa (nulo é diferente de ausente)", async () => {
      const { visto: _removido, ...semVisto } = PAIS_VALIDO;
      await expect(lerPais(semVisto)).rejects.toThrow(/visto/);
    });

    it("situação fora do contrato não passa", async () => {
      const visto = { ...VISTO_VALIDO, situacao: "talvez" };
      await expect(lerPais({ ...PAIS_VALIDO, visto })).rejects.toThrow(/visto\.situacao/);
    });

    it("campo de tipo errado ou ausente dentro do visto não passa", async () => {
      const errado = { ...VISTO_VALIDO, aceita_rg: "sim" };
      await expect(lerPais({ ...PAIS_VALIDO, visto: errado })).rejects.toThrow(/aceita_rg/);
      const { fonte: _removida, ...semFonte } = VISTO_VALIDO;
      await expect(lerPais({ ...PAIS_VALIDO, visto: semFonte })).rejects.toThrow(/fonte/);
    });

    it("permanência com tipo desconhecido não passa", async () => {
      const visto = { ...VISTO_VALIDO, permanencia: { tipo: "infinita", texto: null } };
      await expect(lerPais({ ...PAIS_VALIDO, visto })).rejects.toThrow(/permanencia/);
    });
  });
});

const VISTOS_VALIDOS = {
  dados_obtidos: true,
  coletado_em: "2026-10-29T13:04:35Z",
  desatualizado: false,
  fonte: {
    nome: "Wikipédia: Visa requirements for Brazilian citizens",
    url: "https://en.wikipedia.org/wiki/Visa_requirements_for_Brazilian_citizens",
    licenca: "CC BY-SA",
  },
  territorios: [
    { codigo: "AR", situacao: "isento", aceita_rg: true },
    { codigo: "US", situacao: "visto_exigido", aceita_rg: false },
    { codigo: "BR", situacao: "nao_se_aplica", aceita_rg: false },
  ],
};

describe("GET /vistos (feature 002)", () => {
  async function lerVistos(corpo: unknown) {
    const { cliente, fetchFalso } = clienteCom(respostaJson(corpo));
    return { vistos: await cliente.obterVistos(), fetchFalso };
  }

  it("obterVistos chama /vistos e devolve a resposta tipada", async () => {
    const { vistos, fetchFalso } = await lerVistos(VISTOS_VALIDOS);
    expect(fetchFalso.mock.calls[0]?.[0]).toBe("http://api.exemplo/api/v1/vistos");
    expect(vistos.dados_obtidos).toBe(true);
    expect(vistos.coletado_em).toBe("2026-10-29T13:04:35Z");
    expect(vistos.fonte.licenca).toBe("CC BY-SA");
    expect(vistos.territorios[0]).toEqual({ codigo: "AR", situacao: "isento", aceita_rg: true });
  });

  it("repassa o sinal de cancelamento ao fetch", async () => {
    const { cliente, fetchFalso } = clienteCom(respostaJson(VISTOS_VALIDOS));
    const controle = new AbortController();
    await cliente.obterVistos(controle.signal);
    expect(fetchFalso.mock.calls[0]?.[1]?.signal).toBe(controle.signal);
  });

  it("aceita antes da primeira coleta: sem dados, sem data e tudo 'sem informação'", async () => {
    const { vistos } = await lerVistos({
      ...VISTOS_VALIDOS,
      dados_obtidos: false,
      coletado_em: null,
      territorios: [
        { codigo: "AR", situacao: "sem_informacao", aceita_rg: false },
        { codigo: "BR", situacao: "nao_se_aplica", aceita_rg: false },
      ],
    });
    expect(vistos.dados_obtidos).toBe(false);
    expect(vistos.coletado_em).toBeNull();
  });

  it("situação fora do contrato não passa", async () => {
    const corpo = {
      ...VISTOS_VALIDOS,
      territorios: [{ codigo: "AR", situacao: "talvez", aceita_rg: false }],
    };
    await expect(lerVistos(corpo)).rejects.toThrow(/territorios\[0\]\.situacao/);
  });

  it("campo ausente ou de tipo errado não passa", async () => {
    const { dados_obtidos: _removido, ...semCampo } = VISTOS_VALIDOS;
    await expect(lerVistos(semCampo)).rejects.toThrow(/dados_obtidos/);
    const rgErrado = {
      ...VISTOS_VALIDOS,
      territorios: [{ codigo: "AR", situacao: "isento", aceita_rg: "sim" }],
    };
    await expect(lerVistos(rgErrado)).rejects.toThrow(/aceita_rg/);
    await expect(lerVistos({ ...VISTOS_VALIDOS, fonte: null })).rejects.toThrow(/fonte/);
    await expect(lerVistos({ ...VISTOS_VALIDOS, territorios: "AR" })).rejects.toThrow(
      /territorios/,
    );
  });

  it("'não se aplica' só vale para o Brasil", async () => {
    const corpo = {
      ...VISTOS_VALIDOS,
      territorios: [{ codigo: "AR", situacao: "nao_se_aplica", aceita_rg: false }],
    };
    await expect(lerVistos(corpo)).rejects.toThrow(/situacao/);
  });

  it("erro 5xx e falha de rede viram ErroDeApi", async () => {
    const { cliente } = clienteCom(respostaJson({ detalhe: "indisponível" }, 503));
    await expect(cliente.obterVistos()).rejects.toMatchObject({ status: 503 });
    const { cliente: semRede } = clienteCom(new TypeError("Failed to fetch"));
    await expect(semRede.obterVistos()).rejects.toMatchObject({ status: 0 });
  });
});
