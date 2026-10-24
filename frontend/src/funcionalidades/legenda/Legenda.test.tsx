import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NIVEIS, ORDEM_DA_LEGENDA } from "../../compartilhado/niveis";
import { Legenda } from "./Legenda";

describe("Legenda", () => {
  it("explica os quatro níveis com texto, na ordem da legenda", () => {
    render(<Legenda />);
    const legenda = screen.getByRole("region", { name: "Legenda" });
    const itens = within(legenda).getAllByRole("listitem");

    // os quatro níveis, mais o item da região mais grave
    expect(itens).toHaveLength(ORDEM_DA_LEGENDA.length + 1);
    ORDEM_DA_LEGENDA.forEach((nivel, i) => {
      expect(itens[i]).toHaveTextContent(NIVEIS[nivel].rotulo);
    });
  });

  it("nenhum nível depende só da cor: cada um tem o texto e a amostra de cor é decorativa", () => {
    render(<Legenda />);
    for (const nivel of ORDEM_DA_LEGENDA) {
      const item = screen.getByText(NIVEIS[nivel].rotulo).closest("li");
      expect(item).not.toBeNull();
      const amostra = item?.querySelector("[data-amostra]");
      expect(amostra).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("tem o item 'Região mais grave'", () => {
    render(<Legenda />);
    const item = screen.getByText("Região mais grave").closest("li");
    expect(item).toHaveTextContent(/borda/i);
  });

  it("avisa que 'sem alerta' não é recomendação de viagem", () => {
    render(<Legenda />);
    expect(screen.getByText(/não significa que o governo recomenda a viagem/i)).toBeVisible();
  });

  it("tem o link para 'Sobre as fronteiras deste mapa'", () => {
    render(<Legenda />);
    expect(screen.getByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeVisible();
  });
});
