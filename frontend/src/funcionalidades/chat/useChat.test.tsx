import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErroDeApi, type RespostaDoChat } from "../../servicos/api/cliente";
import { criarApiSimulada } from "../../testes/api-simulada";
import { RESPOSTA_DO_CHAT_EXEMPLO } from "../../testes/dados-exemplo";
import { useChat } from "./useChat";

const MENSAGEM_DE_FALHA = "Não foi possível responder agora. Tente de novo em instantes.";

function textoDe(paragrafos: readonly (readonly { texto: string }[])[] | undefined): string {
  return (paragrafos ?? [])
    .flat()
    .map((t) => t.texto)
    .join("");
}

describe("useChat", () => {
  it("guarda a pergunta e a resposta, só localmente", async () => {
    const api = criarApiSimulada();
    const { result } = renderHook(() => useChat(api.cliente));
    expect(result.current.mensagens).toEqual([]);

    act(() => result.current.enviar("  visto Japão  "));
    expect(api.perguntarAoChat).toHaveBeenCalledWith("visto Japão");
    expect(result.current.respondendo).toBe(true);
    expect(result.current.mensagens).toHaveLength(1);
    expect(result.current.mensagens[0]?.autor).toBe("pessoa");
    expect(textoDe(result.current.mensagens[0]?.paragrafos)).toBe("visto Japão");

    await waitFor(() => expect(result.current.respondendo).toBe(false));
    expect(result.current.mensagens).toHaveLength(2);
    expect(result.current.mensagens[1]?.autor).toBe("chat");
    expect(result.current.mensagens[1]?.paragrafos).toEqual(RESPOSTA_DO_CHAT_EXEMPLO.paragrafos);
  });

  it("enquanto responde, não aceita outra pergunta", async () => {
    let responder: (r: RespostaDoChat) => void = () => undefined;
    const api = criarApiSimulada();
    api.perguntarAoChat.mockImplementationOnce(
      () => new Promise<RespostaDoChat>((resolve) => (responder = resolve)),
    );
    const { result } = renderHook(() => useChat(api.cliente));

    act(() => {
      result.current.enviar("primeira");
      result.current.enviar("segunda"); // mesmo render: `respondendo` ainda é o antigo
    });
    act(() => result.current.enviar("terceira"));
    expect(api.perguntarAoChat).toHaveBeenCalledTimes(1);
    expect(result.current.mensagens).toHaveLength(1);

    await act(async () => {
      responder(RESPOSTA_DO_CHAT_EXEMPLO);
      await Promise.resolve();
    });
    expect(result.current.respondendo).toBe(false);
    act(() => result.current.enviar("quarta"));
    expect(api.perguntarAoChat).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(result.current.respondendo).toBe(false));
  });

  it("pergunta vazia ou só com espaços não é enviada", () => {
    const api = criarApiSimulada();
    const { result } = renderHook(() => useChat(api.cliente));
    act(() => result.current.enviar(""));
    act(() => result.current.enviar("   "));
    expect(api.perguntarAoChat).not.toHaveBeenCalled();
    expect(result.current.mensagens).toEqual([]);
  });

  it("429 vira mensagem com o detalhe do servidor", async () => {
    const detalhe = "Você chegou ao limite de 20 perguntas por hora. Tente de novo em 3 min.";
    const api = criarApiSimulada({ chat: new ErroDeApi(429, detalhe) });
    const { result } = renderHook(() => useChat(api.cliente));
    act(() => result.current.enviar("visto Japão"));
    await waitFor(() => expect(result.current.mensagens).toHaveLength(2));
    expect(textoDe(result.current.mensagens[1]?.paragrafos)).toBe(detalhe);
    expect(result.current.respondendo).toBe(false);
  });

  it.each([
    ["5xx", new ErroDeApi(503, "indisponível")],
    ["rede", new ErroDeApi(0, "Não foi possível falar com o servidor")],
    ["422", new ErroDeApi(422, "campo inválido")],
  ])("falha (%s) vira a mensagem genérica", async (_nome, erro) => {
    const api = criarApiSimulada({ chat: erro });
    const { result } = renderHook(() => useChat(api.cliente));
    act(() => result.current.enviar("visto Japão"));
    await waitFor(() => expect(result.current.mensagens).toHaveLength(2));
    expect(textoDe(result.current.mensagens[1]?.paragrafos)).toBe(MENSAGEM_DE_FALHA);
    expect(result.current.respondendo).toBe(false);
  });
});
