import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SobreFronteiras } from "./SobreFronteiras";

const NOME = "Sobre as fronteiras deste mapa";

async function abrir() {
  const usuario = userEvent.setup();
  render(<SobreFronteiras />);
  const gatilho = screen.getByRole("button", { name: NOME });
  await usuario.click(gatilho);
  return { usuario, gatilho, dialogo: screen.getByRole("dialog", { name: NOME }) };
}

describe("SobreFronteiras", () => {
  it("abre como modal, sem roteador", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(window.location.hash).toBe("");
  });

  it("explica os casos especiais: Kosovo, Taiwan e Malvinas", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveTextContent(/Kosovo/);
    expect(dialogo).toHaveTextContent(/Taiwan/);
    expect(dialogo).toHaveTextContent(/Malvinas/);
    expect(dialogo).toHaveTextContent(/posição (oficial )?do Brasil/i);
  });

  it("explica as áreas neutras, sem painel: Saara Ocidental e Antártida", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveTextContent(/Saara Ocidental/);
    expect(dialogo).toHaveTextContent(/Antártida/);
    expect(dialogo).toHaveTextContent(/sem painel/i);
  });

  it("explica as dependências", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveTextContent(/dependências/i);
    expect(dialogo).toHaveTextContent(/mais recente/i);
  });

  it("prende o foco enquanto está aberto", async () => {
    const { usuario, dialogo } = await abrir();
    for (let i = 0; i < 4; i++) {
      await usuario.tab();
      expect(dialogo).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("Esc fecha e o foco volta ao link", async () => {
    const { usuario, gatilho } = await abrir();
    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(gatilho).toHaveFocus();
  });

  it("o botão Fechar também fecha", async () => {
    const { usuario, gatilho, dialogo } = await abrir();
    await usuario.click(within(dialogo).getByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(gatilho).toHaveFocus();
  });
});
