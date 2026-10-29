import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { ProvedorDeEstado, useEstado } from "../../estado/contexto";
import { ErroDeApi } from "../../servicos/api/cliente";
import { criarApiSimulada } from "../../testes/api-simulada";
import { VISTOS_EXEMPLO } from "../../testes/dados-exemplo";
import { useVistos } from "./useVistos";

afterEach(cleanup);

function Sonda({ cliente }: { cliente: Parameters<typeof useVistos>[0] }) {
  const { estado: global, despachar } = useEstado();
  const { estado, tentarDeNovo } = useVistos(cliente, global.modo);
  return (
    <div>
      <p data-testid="situacao">{estado.situacao}</p>
      <p data-testid="mensagem">{estado.situacao === "erro" ? estado.mensagem : ""}</p>
      <p data-testid="territorios">
        {estado.situacao === "pronto" ? estado.dados.territorios.length : ""}
      </p>
      <button onClick={() => despachar({ tipo: "trocar-modo", modo: "vistos" })}>vistos</button>
      <button onClick={() => despachar({ tipo: "trocar-modo", modo: "alertas" })}>alertas</button>
      <button onClick={tentarDeNovo}>de novo</button>
    </div>
  );
}

function montar(respostas: Parameters<typeof criarApiSimulada>[0] = {}) {
  const api = criarApiSimulada(respostas);
  render(
    <ProvedorDeEstado>
      <Sonda cliente={api.cliente} />
    </ProvedorDeEstado>,
  );
  return api;
}

const situacao = () => screen.getByTestId("situacao").textContent;

describe("useVistos", () => {
  it("não busca nada no carregamento nem no modo 'Alertas'", async () => {
    const api = montar();
    await act(async () => {});
    expect(api.obterVistos).not.toHaveBeenCalled();
    expect(situacao()).toBe("nao_pedido");
    await userEvent.setup().click(screen.getByRole("button", { name: "alertas" }));
    expect(api.obterVistos).not.toHaveBeenCalled();
  });

  it("busca uma vez ao escolher 'Vistos' e guarda a resposta", async () => {
    const api = montar();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(situacao()).toBe("pronto"));
    expect(api.obterVistos).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("territorios")).toHaveTextContent(
      String(VISTOS_EXEMPLO.territorios.length),
    );

    // voltar e escolher de novo usa a resposta guardada
    await usuario.click(screen.getByRole("button", { name: "alertas" }));
    await usuario.click(screen.getByRole("button", { name: "vistos" }));
    expect(api.obterVistos).toHaveBeenCalledTimes(1);
    expect(situacao()).toBe("pronto");
  });

  it("passa por 'carregando' antes de chegar a 'pronto'", async () => {
    let resolver: (() => void) | undefined;
    const api = criarApiSimulada();
    api.obterVistos.mockImplementation(
      () => new Promise((resolve) => (resolver = () => resolve(VISTOS_EXEMPLO))),
    );
    render(
      <ProvedorDeEstado>
        <Sonda cliente={api.cliente} />
      </ProvedorDeEstado>,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(situacao()).toBe("carregando"));
    await act(async () => resolver?.());
    await waitFor(() => expect(situacao()).toBe("pronto"));
  });

  it.each([
    ["rede", new ErroDeApi(0, "Não foi possível falar com o servidor")],
    ["5xx", new ErroDeApi(503, "indisponível")],
    ["fora do contrato", new ErroDeApi(200, 'Resposta inválida da API (campo "territorios")')],
  ])("erro de %s vira 'erro' com a mensagem", async (_nome, erro) => {
    montar({ vistos: erro });
    await userEvent.setup().click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(situacao()).toBe("erro"));
    expect(screen.getByTestId("mensagem")).toHaveTextContent(erro.message);
  });

  it("'Tentar de novo' busca outra vez e, em sucesso, chega a 'pronto'", async () => {
    const api = criarApiSimulada({ vistos: new ErroDeApi(503, "indisponível") });
    render(
      <ProvedorDeEstado>
        <Sonda cliente={api.cliente} />
      </ProvedorDeEstado>,
    );
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(situacao()).toBe("erro"));

    api.obterVistos.mockResolvedValue(VISTOS_EXEMPLO);
    await usuario.click(screen.getByRole("button", { name: "de novo" }));
    await waitFor(() => expect(situacao()).toBe("pronto"));
    expect(api.obterVistos).toHaveBeenCalledTimes(2);
  });

  it("depois de um erro, escolher o modo de novo não refaz a chamada sozinho", async () => {
    const api = montar({ vistos: new ErroDeApi(503, "indisponível") });
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(situacao()).toBe("erro"));
    await usuario.click(screen.getByRole("button", { name: "alertas" }));
    await usuario.click(screen.getByRole("button", { name: "vistos" }));
    expect(api.obterVistos).toHaveBeenCalledTimes(1);
    expect(situacao()).toBe("erro");
  });

  it("cancela a busca ao desmontar e não grava a resposta que chegar depois", async () => {
    let sinal: AbortSignal | undefined;
    const api = criarApiSimulada();
    api.obterVistos.mockImplementation((s) => {
      sinal = s;
      return new Promise(() => {});
    });
    const { unmount } = render(
      <ProvedorDeEstado>
        <Sonda cliente={api.cliente} />
      </ProvedorDeEstado>,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "vistos" }));
    await waitFor(() => expect(sinal).toBeDefined());
    unmount();
    expect(sinal?.aborted).toBe(true);
  });
});
