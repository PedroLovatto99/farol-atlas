import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ProvedorDeEstado, useEstado } from "./contexto";

function Consumidor() {
  const { estado, despachar } = useEstado();
  return (
    <div>
      <p data-testid="selecionado">{estado.selecionado ?? "ninguém"}</p>
      <button onClick={() => despachar({ tipo: "selecionar", codigo: "DK" })}>selecionar</button>
      <button onClick={() => despachar({ tipo: "limpar-selecao" })}>limpar</button>
    </div>
  );
}

describe("contexto do estado", () => {
  it("distribui o estado e as ações para os componentes", async () => {
    const usuario = userEvent.setup();
    render(
      <ProvedorDeEstado>
        <Consumidor />
      </ProvedorDeEstado>,
    );
    expect(screen.getByTestId("selecionado")).toHaveTextContent("ninguém");
    await usuario.click(screen.getByRole("button", { name: "selecionar" }));
    expect(screen.getByTestId("selecionado")).toHaveTextContent("DK");
    await usuario.click(screen.getByRole("button", { name: "limpar" }));
    expect(screen.getByTestId("selecionado")).toHaveTextContent("ninguém");
  });

  it("falha com mensagem clara fora do provedor", () => {
    expect(() => render(<Consumidor />)).toThrow(/ProvedorDeEstado/);
  });
});
