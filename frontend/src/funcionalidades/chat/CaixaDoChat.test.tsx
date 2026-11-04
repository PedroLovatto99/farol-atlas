import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { URL_DO_PORTAL_CONSULAR } from "../aviso/Aviso";
import { CaixaDoChat } from "./CaixaDoChat";
import type { MensagemDoChat } from "./useChat";

function resposta(paragrafos: MensagemDoChat["paragrafos"]): MensagemDoChat {
  return { id: 1, autor: "chat", paragrafos };
}

function abrir(mensagens: readonly MensagemDoChat[] = [], respondendo = false) {
  const onEnviar = vi.fn<(pergunta: string) => void>();
  const onFechar = vi.fn<() => void>();
  render(
    <CaixaDoChat
      mensagens={mensagens}
      respondendo={respondendo}
      onEnviar={onEnviar}
      onFechar={onFechar}
    />,
  );
  return { onEnviar, onFechar };
}

const campo = () => screen.getByRole("textbox", { name: "Sua pergunta" });

describe("CaixaDoChat", () => {
  it("ao abrir, o foco vai para o campo", () => {
    abrir();
    expect(campo()).toHaveFocus();
  });

  it("é um diálogo não modal: o resto da tela continua acessível", () => {
    abrir();
    expect(screen.getByRole("dialog", { name: "Chat" })).not.toHaveAttribute("aria-modal");
  });

  it("mostra o aviso fixo com o link do Portal Consular", () => {
    abrir();
    const link = screen.getByRole("link", { name: "Portal Consular" });
    expect(link).toHaveAttribute("href", URL_DO_PORTAL_CONSULAR);
    expect(link.closest("p")).toHaveTextContent(
      "As respostas são montadas automaticamente a partir dos dados do site e devem ser conferidas no Portal Consular",
    );
  });

  it("limita a 300 caracteres e conta o que foi digitado", async () => {
    abrir();
    expect(campo()).toHaveAttribute("maxLength", "300");
    expect(screen.getByText("0/300")).toBeInTheDocument();
    await userEvent.setup().type(campo(), "visto");
    expect(screen.getByText("5/300")).toBeInTheDocument();
  });

  it("Enter envia a pergunta e limpa o campo", async () => {
    const { onEnviar } = abrir();
    await userEvent.setup().type(campo(), "visto Japão{Enter}");
    expect(onEnviar).toHaveBeenCalledWith("visto Japão");
    expect(campo()).toHaveValue("");
  });

  it("não envia campo vazio nem só com espaços", async () => {
    const { onEnviar } = abrir();
    const usuario = userEvent.setup();
    await usuario.type(campo(), "   {Enter}");
    await usuario.click(screen.getByRole("button", { name: "Enviar" }));
    expect(onEnviar).not.toHaveBeenCalled();
  });

  it("respondendo: mostra o estado e desabilita campo e envio", () => {
    abrir([], true);
    expect(screen.getByText("Respondendo…")).toBeInTheDocument();
    expect(campo()).toBeDisabled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("o foco volta ao campo quando a resposta chega", () => {
    const props = { mensagens: [], onEnviar: vi.fn(), onFechar: vi.fn() };
    const { rerender } = render(<CaixaDoChat {...props} respondendo />);
    expect(campo()).not.toHaveFocus();
    rerender(<CaixaDoChat {...props} respondendo={false} />);
    expect(campo()).toHaveFocus();
  });

  it("a resposta não tira o foco de quem já saiu da caixa", () => {
    const props = { mensagens: [], onEnviar: vi.fn(), onFechar: vi.fn() };
    const { rerender } = render(
      <>
        <input aria-label="Buscar país" />
        <CaixaDoChat {...props} respondendo />
      </>,
    );
    const busca = screen.getByRole("textbox", { name: "Buscar país" });
    busca.focus();
    rerender(
      <>
        <input aria-label="Buscar país" />
        <CaixaDoChat {...props} respondendo={false} />
      </>,
    );
    expect(busca).toHaveFocus();
  });

  it("ao abrir, o foco vai para o campo mesmo vindo do botão", () => {
    render(<button type="button">Abrir</button>);
    screen.getByRole("button", { name: "Abrir" }).focus();
    abrir();
    expect(campo()).toHaveFocus();
  });

  it("o Esc tratado pelo chat sai marcado, para o painel não fechar junto", () => {
    abrir();
    // fireEvent devolve false quando alguém chamou preventDefault
    expect(fireEvent.keyDown(document, { key: "Escape" })).toBe(false);
  });

  it("Esc pede para fechar", async () => {
    const { onFechar } = abrir();
    await userEvent.setup().keyboard("{Escape}");
    expect(onFechar).toHaveBeenCalledTimes(1);
  });

  it("com um diálogo modal aberto por cima, o Esc é dele", async () => {
    const { onFechar } = abrir();
    render(<div role="dialog" aria-modal="true" aria-label="Sobre" />);
    await userEvent.setup().keyboard("{Escape}");
    expect(onFechar).not.toHaveBeenCalled();
  });

  it("as mensagens ficam numa região aria-live polite", () => {
    abrir([resposta([[{ texto: "Sim, brasileiros precisam de visto.", url: null }]])]);
    const regiao = screen.getByText("Sim, brasileiros precisam de visto.").closest("[aria-live]");
    expect(regiao).toHaveAttribute("aria-live", "polite");
  });

  it("um parágrafo por item e trechos na ordem", () => {
    abrir([
      resposta([
        [{ texto: "Primeiro.", url: null }],
        [
          { texto: "Fonte: ", url: null },
          { texto: "Wikipédia", url: "https://en.wikipedia.org/wiki/X" },
          { texto: ", dado de 01/11/2026.", url: null },
        ],
      ]),
    ]);
    const ultimo = screen.getByRole("link", { name: "Wikipédia" }).closest("p");
    expect(ultimo).toHaveTextContent("Fonte: Wikipédia, dado de 01/11/2026.");
    expect(screen.getByText("Primeiro.").closest("p")).not.toBe(ultimo);
  });

  it("trecho com url web vira link que abre em outra aba", () => {
    abrir([resposta([[{ texto: "Alerta", url: "https://www.gov.br/alerta" }]])]);
    const link = screen.getByRole("link", { name: "Alerta" });
    expect(link).toHaveAttribute("href", "https://www.gov.br/alerta");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("trecho com url javascript: vira texto", () => {
    abrir([resposta([[{ texto: "Clique", url: "javascript:alert(1)" }]])]);
    expect(screen.queryByRole("link", { name: "Clique" })).not.toBeInTheDocument();
    expect(screen.getByText("Clique")).toBeInTheDocument();
  });

  it("texto com marcação aparece como texto", () => {
    const marcacao = '<img src=x onerror="alert(1)"><b>negrito</b>';
    abrir([resposta([[{ texto: marcacao, url: null }]])]);
    const trecho = screen.getByText(marcacao);
    expect(trecho.querySelector("img, b")).toBeNull();
  });

  it("diz quem falou sem depender só da cor", () => {
    abrir([
      { id: 0, autor: "pessoa", paragrafos: [[{ texto: "visto Japão", url: null }]] },
      { id: 1, autor: "chat", paragrafos: [[{ texto: "Não precisa.", url: null }]] },
    ]);
    expect(screen.getByText("Você:")).toBeInTheDocument();
    expect(screen.getByText("Chat:")).toBeInTheDocument();
  });
});
