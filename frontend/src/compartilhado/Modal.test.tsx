import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./Modal";

function Exemplo({ conteudo = "Conteúdo do modal" }: { conteudo?: ReactNode }) {
  const [aberto, setAberto] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setAberto(true)}>
        Abrir
      </button>
      <Modal aberto={aberto} titulo="Título do modal" onFechar={() => setAberto(false)}>
        <a href="#interno">link interno</a>
        <p>{conteudo}</p>
      </Modal>
    </>
  );
}

describe("Modal", () => {
  it("não aparece enquanto está fechado", () => {
    render(
      <Modal aberto={false} titulo="Título" onFechar={() => {}}>
        <p>escondido</p>
      </Modal>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText("escondido")).not.toBeInTheDocument();
  });

  it("é um diálogo modal com o título como nome", async () => {
    render(<Exemplo />);
    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));

    const dialogo = screen.getByRole("dialog", { name: "Título do modal" });
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(dialogo).toHaveTextContent("Conteúdo do modal");
  });

  it("leva o foco para dentro do diálogo ao abrir", async () => {
    render(<Exemplo />);
    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));
    expect(screen.getByRole("dialog")).toContainElement(document.activeElement as HTMLElement);
  });

  it("prende o foco: Tab e Shift+Tab giram dentro do diálogo", async () => {
    const usuario = userEvent.setup();
    render(<Exemplo />);
    await usuario.click(screen.getByRole("button", { name: "Abrir" }));
    const dialogo = screen.getByRole("dialog");

    for (let i = 0; i < 6; i++) {
      await usuario.tab();
      expect(dialogo).toContainElement(document.activeElement as HTMLElement);
    }
    for (let i = 0; i < 6; i++) {
      await usuario.tab({ shift: true });
      expect(dialogo).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("Esc fecha e o foco volta ao elemento que abriu", async () => {
    const usuario = userEvent.setup();
    render(<Exemplo />);
    const abrir = screen.getByRole("button", { name: "Abrir" });
    await usuario.click(abrir);

    await usuario.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(abrir).toHaveFocus();
  });

  it("o botão Fechar fecha e devolve o foco", async () => {
    const usuario = userEvent.setup();
    render(<Exemplo />);
    const abrir = screen.getByRole("button", { name: "Abrir" });
    await usuario.click(abrir);

    await usuario.click(screen.getByRole("button", { name: "Fechar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(abrir).toHaveFocus();
  });

  it("clicar fora do diálogo fecha; clicar dentro não", async () => {
    const usuario = userEvent.setup();
    const aoFechar = vi.fn();
    render(
      <Modal aberto titulo="Título" onFechar={aoFechar}>
        <p>dentro</p>
      </Modal>,
    );

    await usuario.click(screen.getByText("dentro"));
    expect(aoFechar).not.toHaveBeenCalled();

    await usuario.click(screen.getByTestId("fundo-do-modal"));
    expect(aoFechar).toHaveBeenCalledTimes(1);
  });

  it("insere o conteúdo como texto, nunca como HTML", async () => {
    const perigoso = '<img src="x" onerror="alert(1)"><script>alert(2)</script>';
    render(<Exemplo conteudo={perigoso} />);
    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));

    const dialogo = screen.getByRole("dialog");
    expect(dialogo).toHaveTextContent(perigoso);
    expect(dialogo.querySelector("img")).toBeNull();
    expect(dialogo.querySelector("script")).toBeNull();
  });
});
