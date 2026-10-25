import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErroDeApi, type Pais } from "../../servicos/api/cliente";
import { criarApiSimulada } from "../../testes/api-simulada";
import { criarPais, PAIS_EXEMPLO } from "../../testes/dados-exemplo";
import { usePais } from "./usePais";

const LIBANO: Pais = criarPais({ codigo: "LB", nome: "Líbano" });

describe("usePais", () => {
  it("sem seleção não chama a API", () => {
    const api = criarApiSimulada();
    const { result } = renderHook(() => usePais(api.cliente, null));
    expect(result.current.estado).toEqual({ situacao: "ocioso" });
    expect(api.obterPais).not.toHaveBeenCalled();
  });

  it("faz uma única chamada por seleção e entrega o painel", async () => {
    const api = criarApiSimulada();
    const { result, rerender } = renderHook(() => usePais(api.cliente, "DK"));
    expect(result.current.estado).toEqual({ situacao: "carregando" });

    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    rerender();
    rerender();
    expect(api.obterPais).toHaveBeenCalledTimes(1);
    expect(api.obterPais).toHaveBeenCalledWith("DK", expect.any(AbortSignal));
    expect(result.current.estado).toEqual({ situacao: "pronto", pais: PAIS_EXEMPLO });
  });

  it("trocar de país cancela a chamada anterior e nunca mostra o painel do país errado", async () => {
    const api = criarApiSimulada({ paises: { DK: PAIS_EXEMPLO, LB: LIBANO } });
    let resolverDinamarca: (pais: Pais) => void = () => {};
    api.obterPais.mockImplementationOnce(
      () => new Promise<Pais>((resolver) => (resolverDinamarca = resolver)),
    );

    const { result, rerender } = renderHook(({ codigo }) => usePais(api.cliente, codigo), {
      initialProps: { codigo: "DK" as string | null },
    });
    const sinalDaDinamarca = api.obterPais.mock.calls[0]?.[1];

    rerender({ codigo: "LB" });
    expect(sinalDaDinamarca?.aborted).toBe(true);
    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    expect(result.current.estado).toEqual({ situacao: "pronto", pais: LIBANO });

    // a resposta atrasada da Dinamarca chega depois e é ignorada
    await act(async () => resolverDinamarca(PAIS_EXEMPLO));
    expect(result.current.estado).toEqual({ situacao: "pronto", pais: LIBANO });
  });

  it("limpar a seleção volta a ocioso", async () => {
    const api = criarApiSimulada();
    const { result, rerender } = renderHook(({ codigo }) => usePais(api.cliente, codigo), {
      initialProps: { codigo: "DK" as string | null },
    });
    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    rerender({ codigo: null });
    expect(result.current.estado).toEqual({ situacao: "ocioso" });
  });

  it("no erro, guarda a mensagem e tentarDeNovo repete a chamada", async () => {
    const api = criarApiSimulada({ paises: { DK: new ErroDeApi(503, "Banco indisponível") } });
    const { result } = renderHook(() => usePais(api.cliente, "DK"));
    await waitFor(() =>
      expect(result.current.estado).toEqual({ situacao: "erro", mensagem: "Banco indisponível" }),
    );

    api.obterPais.mockResolvedValueOnce(PAIS_EXEMPLO);
    act(() => result.current.tentarDeNovo());
    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    expect(api.obterPais).toHaveBeenCalledTimes(2);
  });

  it("erro que não é da API vira uma mensagem padrão", async () => {
    const api = criarApiSimulada();
    api.obterPais.mockRejectedValueOnce(new TypeError("falhou"));
    const { result } = renderHook(() => usePais(api.cliente, "DK"));
    await waitFor(() => expect(result.current.estado.situacao).toBe("erro"));
    expect(result.current.estado).toMatchObject({
      mensagem: expect.stringMatching(/não foi possível carregar/i),
    });
  });
});
