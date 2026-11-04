import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { criarApiSimulada } from "../../testes/api-simulada";
import { BotaoDoChat } from "./BotaoDoChat";

function abrir() {
  const api = criarApiSimulada();
  render(<BotaoDoChat cliente={api.cliente} />);
  return { api, usuario: userEvent.setup() };
}

const botaoDeAbrir = () => screen.getByRole("button", { name: "Abrir chat" });
const botaoDeFechar = () => screen.getByRole("button", { name: "Fechar chat" });

describe("BotaoDoChat", () => {
  it("começa fechado e não chama a API", () => {
    const { api } = abrir();
    expect(botaoDeAbrir()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.perguntarAoChat).not.toHaveBeenCalled();
  });

  it("abre e fecha pelo botão, trocando o rótulo", async () => {
    const { usuario } = abrir();
    await usuario.click(botaoDeAbrir());
    expect(botaoDeFechar()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("dialog", { name: "Chat" })).toBeInTheDocument();
    await usuario.click(botaoDeFechar());
    expect(botaoDeAbrir()).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("abrir leva o foco ao campo; Esc fecha e devolve o foco ao botão", async () => {
    const { usuario } = abrir();
    botaoDeAbrir().focus();
    await usuario.keyboard("{Enter}");
    expect(screen.getByRole("textbox", { name: "Sua pergunta" })).toHaveFocus();
    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(botaoDeAbrir()).toHaveFocus();
  });

  it("perguntar só pelo teclado mostra a resposta, que continua lá ao reabrir", async () => {
    const { api, usuario } = abrir();
    await usuario.click(botaoDeAbrir());
    await usuario.keyboard("visto Japão{Enter}");
    const resposta = "Não, brasileiros não precisam de visto para o Japão.";
    expect(await screen.findByText(resposta)).toBeInTheDocument();
    expect(api.perguntarAoChat).toHaveBeenCalledWith("visto Japão");
    await usuario.keyboard("{Escape}");
    await usuario.click(botaoDeAbrir());
    expect(screen.getByText(resposta)).toBeInTheDocument();
  });
});
