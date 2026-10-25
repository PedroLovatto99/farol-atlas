import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Sobre } from "./Sobre";

async function abrir() {
  const usuario = userEvent.setup();
  render(<Sobre />);
  const gatilho = screen.getByRole("button", { name: "Sobre" });
  await usuario.click(gatilho);
  return { usuario, gatilho, dialogo: screen.getByRole("dialog", { name: "Sobre o Farol Atlas" }) };
}

describe("Sobre", () => {
  it("abre como modal, sem roteador", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(window.location.hash).toBe("");
  });

  it("diz que não é um serviço oficial e leva ao Itamaraty", async () => {
    const { dialogo } = await abrir();
    expect(dialogo).toHaveTextContent(/não oficial|não é um serviço oficial/i);
    const link = within(dialogo).getByRole("link", { name: /portal consular do itamaraty/i });
    expect(link).toHaveAttribute("href", "https://www.gov.br/mre/pt-br/assuntos/portal-consular");
  });

  it("atribui as fontes: Natural Earth, Wikipédia (CC BY-SA) e Itamaraty", async () => {
    const { dialogo } = await abrir();
    expect(within(dialogo).getByRole("link", { name: /Natural Earth/ })).toHaveAttribute(
      "href",
      "https://www.naturalearthdata.com/",
    );
    const wikipedia = within(dialogo).getByRole("link", { name: /Wikipédia/ });
    expect(wikipedia).toHaveAttribute(
      "href",
      "https://en.wikipedia.org/wiki/List_of_diplomatic_missions_of_Brazil",
    );
    expect(dialogo).toHaveTextContent("CC BY-SA");
    expect(dialogo).toHaveTextContent(/Itamaraty/);
  });

  it("prende o foco enquanto está aberto", async () => {
    const { usuario, dialogo } = await abrir();
    for (let i = 0; i < 8; i++) {
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
});
