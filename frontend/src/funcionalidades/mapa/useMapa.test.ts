import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErroDeApi } from "../../servicos/api/cliente";
import { criarApiSimulada } from "../../testes/api-simulada";
import { MAPA_EXEMPLO } from "../../testes/dados-exemplo";
import { useMapa } from "./useMapa";

describe("useMapa", () => {
  it("começa carregando e entrega o mapa com uma única chamada a /mapa", async () => {
    const api = criarApiSimulada();
    const { result, rerender } = renderHook(() => useMapa(api.cliente));

    expect(result.current.estado.situacao).toBe("carregando");
    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    rerender();
    rerender();

    expect(api.obterMapa).toHaveBeenCalledTimes(1);
    expect(api.obterPais).not.toHaveBeenCalled(); // nada de requisição por país no carregamento
    const estado = result.current.estado;
    expect(estado.situacao === "pronto" && estado.mapa).toEqual(MAPA_EXEMPLO);
  });

  it("mostra a mensagem do erro da API", async () => {
    const api = criarApiSimulada({ mapa: new ErroDeApi(503, "Banco indisponível") });
    const { result } = renderHook(() => useMapa(api.cliente));

    await waitFor(() => expect(result.current.estado.situacao).toBe("erro"));
    const estado = result.current.estado;
    expect(estado.situacao === "erro" && estado.mensagem).toBe("Banco indisponível");
  });

  it("falha de rede também vira erro, com mensagem em português", async () => {
    const api = criarApiSimulada();
    api.obterMapa.mockRejectedValueOnce(new Error("socket hang up"));
    const { result } = renderHook(() => useMapa(api.cliente));

    await waitFor(() => expect(result.current.estado.situacao).toBe("erro"));
    const estado = result.current.estado;
    expect(estado.situacao === "erro" && estado.mensagem).toMatch(/não foi possível/i);
  });

  it("tentarDeNovo busca de novo e se recupera do erro", async () => {
    const api = criarApiSimulada();
    api.obterMapa.mockRejectedValueOnce(new ErroDeApi(0, "Não foi possível falar com o servidor"));
    const { result } = renderHook(() => useMapa(api.cliente));
    await waitFor(() => expect(result.current.estado.situacao).toBe("erro"));

    act(() => result.current.tentarDeNovo());
    expect(result.current.estado.situacao).toBe("carregando");
    await waitFor(() => expect(result.current.estado.situacao).toBe("pronto"));
    expect(api.obterMapa).toHaveBeenCalledTimes(2);
  });

  it("cancela a chamada quando o componente sai da tela", async () => {
    const api = criarApiSimulada();
    const { unmount } = renderHook(() => useMapa(api.cliente));
    unmount();
    expect(api.obterMapa.mock.calls[0]?.[0]?.aborted).toBe(true);
  });
});
