import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BotaoDoDaltonismo } from "./BotaoDoDaltonismo";

afterEach(cleanup);

const botao = () => screen.getByRole("button", { name: "Modo daltonismo" });

describe("BotaoDoDaltonismo", () => {
  it.each([true, false])("o nome é sempre 'Modo daltonismo' (ligado: %s)", (ligado) => {
    render(<BotaoDoDaltonismo ligado={ligado} onAlternar={vi.fn()} />);
    expect(botao()).toBeVisible();
  });

  it("aria-pressed acompanha o estado", () => {
    const { rerender } = render(<BotaoDoDaltonismo ligado={false} onAlternar={vi.fn()} />);
    expect(botao()).toHaveAttribute("aria-pressed", "false");
    rerender(<BotaoDoDaltonismo ligado onAlternar={vi.fn()} />);
    expect(botao()).toHaveAttribute("aria-pressed", "true");
  });

  it("o estado aparece também sem depender da cor: a marca só existe com o modo ligado", () => {
    const { container, rerender } = render(
      <BotaoDoDaltonismo ligado={false} onAlternar={vi.fn()} />,
    );
    expect(container.querySelector("svg")).toBeNull();
    rerender(<BotaoDoDaltonismo ligado onAlternar={vi.fn()} />);
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("clique, Enter e Espaço alternam", async () => {
    const aoAlternar = vi.fn();
    const usuario = userEvent.setup();
    render(<BotaoDoDaltonismo ligado={false} onAlternar={aoAlternar} />);
    await usuario.click(botao());
    expect(aoAlternar).toHaveBeenCalledTimes(1);
    botao().focus();
    await usuario.keyboard("{Enter}");
    expect(aoAlternar).toHaveBeenCalledTimes(2);
    await usuario.keyboard(" ");
    expect(aoAlternar).toHaveBeenCalledTimes(3);
  });

  it("não tem animação nem transição", () => {
    render(<BotaoDoDaltonismo ligado onAlternar={vi.fn()} />);
    expect(botao().className).not.toMatch(/animate|transition/);
  });
});
