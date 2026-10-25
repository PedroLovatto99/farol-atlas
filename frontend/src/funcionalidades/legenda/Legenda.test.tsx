import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NIVEIS, ORDEM_DA_LEGENDA, type NivelId } from "../../compartilhado/niveis";
import { Legenda } from "./Legenda";
import { SemNiveisMarcados } from "./SemNiveisMarcados";

function desenhar(niveisMarcados: readonly NivelId[] = ORDEM_DA_LEGENDA) {
  const aoAlternar = vi.fn<(nivel: NivelId) => void>();
  render(<Legenda niveisMarcados={niveisMarcados} onAlternarNivel={aoAlternar} />);
  return aoAlternar;
}

describe("Legenda", () => {
  it("explica os quatro níveis com texto, na ordem da legenda", () => {
    desenhar();
    const legenda = screen.getByRole("region", { name: "Legenda" });
    const itens = within(legenda).getAllByRole("listitem");

    // os quatro níveis, mais o item da região mais grave
    expect(itens).toHaveLength(ORDEM_DA_LEGENDA.length + 1);
    ORDEM_DA_LEGENDA.forEach((nivel, i) => {
      expect(itens[i]).toHaveTextContent(NIVEIS[nivel].rotulo);
    });
  });

  it("nenhum nível depende só da cor: cada um tem o texto e a amostra de cor é decorativa", () => {
    desenhar();
    for (const nivel of ORDEM_DA_LEGENDA) {
      const item = screen.getByText(NIVEIS[nivel].rotulo).closest("li");
      expect(item).not.toBeNull();
      const amostra = item?.querySelector("[data-amostra]");
      expect(amostra).toHaveAttribute("aria-hidden", "true");
    }
  });

  it("tem o item 'Região mais grave'", () => {
    desenhar();
    const item = screen.getByText("Região mais grave").closest("li");
    expect(item).toHaveTextContent(/borda/i);
  });

  it("avisa que 'sem alerta' não é recomendação de viagem", () => {
    desenhar();
    expect(screen.getByText(/não significa que o governo recomenda a viagem/i)).toBeVisible();
  });

  it("tem o link para 'Sobre as fronteiras deste mapa'", () => {
    desenhar();
    expect(screen.getByRole("button", { name: "Sobre as fronteiras deste mapa" })).toBeVisible();
  });
});

describe("Legenda como filtro (FR-024)", () => {
  it("tem uma caixa de marcar por nível, com o rótulo em texto, todas marcadas ao abrir", () => {
    desenhar();
    for (const nivel of ORDEM_DA_LEGENDA) {
      expect(screen.getByRole("checkbox", { name: NIVEIS[nivel].rotulo })).toBeChecked();
    }
    expect(screen.getAllByRole("checkbox")).toHaveLength(ORDEM_DA_LEGENDA.length);
  });

  it("mostra desmarcada a caixa de um nível que não está marcado", () => {
    desenhar(["evitar"]);
    expect(screen.getByRole("checkbox", { name: NIVEIS.evitar.rotulo })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: NIVEIS.sem_alerta.rotulo })).not.toBeChecked();
  });

  it("marcar ou desmarcar uma caixa avisa qual nível mudou", async () => {
    const aoAlternar = desenhar();
    await userEvent.setup().click(screen.getByRole("checkbox", { name: NIVEIS.nao_viajar.rotulo }));
    expect(aoAlternar).toHaveBeenCalledExactlyOnceWith("nao_viajar");
  });

  it("funciona pelo teclado (Espaço marca e desmarca)", async () => {
    const aoAlternar = desenhar();
    screen.getByRole("checkbox", { name: NIVEIS.evitar.rotulo }).focus();
    await userEvent.setup().keyboard(" ");
    expect(aoAlternar).toHaveBeenCalledExactlyOnceWith("evitar");
  });
});

describe("SemNiveisMarcados", () => {
  it("avisa que nenhum nível está marcado e oferece o botão que marca todos", async () => {
    const aoMarcarTodos = vi.fn();
    render(<SemNiveisMarcados onMarcarTodos={aoMarcarTodos} />);
    expect(screen.getByRole("status")).toHaveTextContent(/nenhum nível marcado/i);
    await userEvent.setup().click(screen.getByRole("button", { name: "Marcar todos os níveis" }));
    expect(aoMarcarTodos).toHaveBeenCalledOnce();
  });
});
