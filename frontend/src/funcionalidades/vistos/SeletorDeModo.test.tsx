import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ModoDoGlobo } from "../mapa/tipos";
import { SeletorDeModo } from "./SeletorDeModo";

afterEach(cleanup);

function Tela({ inicial = "alertas" as ModoDoGlobo, aoTrocar = vi.fn() }) {
  const [modo, setModo] = useState<ModoDoGlobo>(inicial);
  return (
    <SeletorDeModo
      modo={modo}
      onTrocar={(novo) => {
        aoTrocar(novo);
        setModo(novo);
      }}
    />
  );
}

const alertas = () => screen.getByRole("radio", { name: "Alertas" });
const vistos = () => screen.getByRole("radio", { name: "Vistos" });

describe("SeletorDeModo", () => {
  it("tem as opções 'Alertas' e 'Vistos', num grupo com nome", () => {
    render(<Tela />);
    expect(screen.getByRole("radiogroup", { name: "O que o globo mostra" })).toBeVisible();
    expect(alertas()).toBeVisible();
    expect(vistos()).toBeVisible();
  });

  it("'Alertas' vem marcado por padrão", () => {
    render(<Tela />);
    expect(alertas()).toBeChecked();
    expect(vistos()).not.toBeChecked();
  });

  it("escolher por clique troca o modo", async () => {
    const aoTrocar = vi.fn();
    render(<Tela aoTrocar={aoTrocar} />);
    const usuario = userEvent.setup();
    await usuario.click(vistos());
    expect(vistos()).toBeChecked();
    expect(aoTrocar).toHaveBeenCalledWith("vistos");
    await usuario.click(alertas());
    expect(aoTrocar).toHaveBeenLastCalledWith("alertas");
  });

  it("clicar no que já está marcado não avisa a tela de novo", async () => {
    const aoTrocar = vi.fn();
    render(<Tela aoTrocar={aoTrocar} />);
    await userEvent.setup().click(alertas());
    expect(aoTrocar).not.toHaveBeenCalled();
  });

  it("funciona pelo teclado: Tab chega ao grupo e as setas trocam o modo", async () => {
    const usuario = userEvent.setup();
    const aoTrocar = vi.fn();
    render(<Tela aoTrocar={aoTrocar} />);
    await usuario.tab();
    expect(alertas()).toHaveFocus();
    await usuario.keyboard("{ArrowRight}");
    expect(vistos()).toBeChecked();
    expect(aoTrocar).toHaveBeenCalledWith("vistos");
    await usuario.keyboard("{ArrowLeft}");
    expect(alertas()).toBeChecked();
  });

  it("o Tab passa pelo grupo uma vez só (só o marcado entra na ordem do Tab)", async () => {
    const usuario = userEvent.setup();
    render(
      <>
        <button>antes</button>
        <Tela />
        <button>depois</button>
      </>,
    );
    await usuario.tab();
    await usuario.tab();
    expect(alertas()).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole("button", { name: "depois" })).toHaveFocus();
  });

  it("cada opção tem alvo de toque de pelo menos 44 px e a ativa tem marca além da cor", () => {
    render(<Tela inicial="vistos" />);
    for (const radio of [alertas(), vistos()]) {
      expect(radio.closest("label")).toHaveClass("min-h-11");
    }
    expect(vistos().closest("label")?.className).toContain("font-semibold");
    expect(alertas().closest("label")?.className).not.toContain("font-semibold");
  });

  it("não cria transição nem animação fora de prefers-reduced-motion", () => {
    const { container } = render(<Tela />);
    const classes = Array.from(container.querySelectorAll("[class]")).flatMap((e) =>
      e.className.toString().split(/\s+/),
    );
    const animadas = classes.filter(
      (c) => /^(transition|animate|duration|ease)/.test(c) && !c.startsWith("motion-reduce:"),
    );
    expect(animadas).toEqual([]);
  });
});
