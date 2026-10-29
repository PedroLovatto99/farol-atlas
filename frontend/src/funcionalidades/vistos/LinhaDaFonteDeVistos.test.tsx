import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { VISTOS_EXEMPLO } from "../../testes/dados-exemplo";
import { LinhaDaFonteDeVistos } from "./LinhaDaFonteDeVistos";

afterEach(cleanup);

describe("LinhaDaFonteDeVistos", () => {
  it("mostra fonte, licença, aviso de não oficial e a data da última coleta válida", () => {
    render(<LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados: VISTOS_EXEMPLO }} />);
    const linha = screen.getByText(/^Vistos:/);
    expect(linha.textContent).toBe(
      "Vistos: Wikipédia (CC BY-SA), fonte não oficial, coletados em 27/10/2026",
    );
  });

  it("'Wikipédia' é um link seguro para o artigo", () => {
    render(<LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados: VISTOS_EXEMPLO }} />);
    const link = screen.getByRole("link", { name: "Wikipédia" });
    expect(link).toHaveAttribute("href", VISTOS_EXEMPLO.fonte.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link).toHaveAttribute("rel", expect.stringContaining("noreferrer"));
  });

  it("endereço da fonte que não é web fica sem link", () => {
    const fonte = { ...VISTOS_EXEMPLO.fonte, url: "javascript:alert(1)" };
    render(
      <LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados: { ...VISTOS_EXEMPLO, fonte } }} />,
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(/Wikipédia/)).toBeVisible();
  });

  it("a data é a de Brasília", () => {
    const dados = { ...VISTOS_EXEMPLO, coletado_em: "2026-10-28T01:30:00Z" }; // 22h30 de 27/10
    render(<LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados }} />);
    expect(screen.getByText(/coletados em 27\/10\/2026/)).toBeVisible();
  });

  it("sem nenhuma coleta válida, diz que ainda não há dados, sem data", () => {
    const dados = { ...VISTOS_EXEMPLO, dados_obtidos: false, coletado_em: null };
    render(<LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados }} />);
    expect(screen.getByText("Vistos: ainda não há dados de visto")).toBeVisible();
    expect(screen.queryByText(/coletados em/)).not.toBeInTheDocument();
  });

  it("com erro, diz que os dados estão indisponíveis", () => {
    render(<LinhaDaFonteDeVistos estado={{ situacao: "erro", mensagem: "caiu" }} />);
    expect(screen.getByText("Vistos: dados indisponíveis no momento")).toBeVisible();
  });

  it("enquanto carrega, avisa em vez de mostrar uma data", () => {
    render(<LinhaDaFonteDeVistos estado={{ situacao: "carregando" }} />);
    expect(screen.getByText("Vistos: carregando…")).toBeVisible();
  });

  it("licença com marcação aparece como texto", () => {
    const fonte = { ...VISTOS_EXEMPLO.fonte, licenca: "<b>x</b>" };
    const { container } = render(
      <LinhaDaFonteDeVistos estado={{ situacao: "pronto", dados: { ...VISTOS_EXEMPLO, fonte } }} />,
    );
    expect(container.querySelector("b")).toBeNull();
    expect(screen.getByText(/<b>x<\/b>/)).toBeVisible();
  });
});
